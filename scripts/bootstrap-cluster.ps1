param(
    [Parameter(Mandatory=$true)][string]$Context,
    [switch]$Local
)
$ErrorActionPreference = 'Stop'
$stockflowRoot = Split-Path $PSScriptRoot -Parent
$stockflowBootstrap = Join-Path $stockflowRoot 'k8s\bootstrap'
$stockflowVersions = Get-Content -LiteralPath (Join-Path $stockflowBootstrap 'versions.json') -Raw | ConvertFrom-Json
$stockflowGenerated = Join-Path $stockflowRoot '.logs\bootstrap'
New-Item -ItemType Directory -Force -Path $stockflowGenerated | Out-Null
$env:HELM_CONFIG_HOME = Join-Path $stockflowRoot '.logs\helm\config'
$env:HELM_CACHE_HOME = Join-Path $stockflowRoot '.logs\helm\cache'
$env:HELM_DATA_HOME = Join-Path $stockflowRoot '.logs\helm\data'

function Invoke-StockFlowTool {
    param([string]$Program, [string[]]$Arguments)
    $ErrorActionPreference = 'Continue'
    $stockflowOutput = & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
    return $stockflowOutput
}
function Ensure-StockFlowNamespace {
    param([string]$Name)
    $stockflowFound = Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'get', 'namespace', $Name, '--ignore-not-found', '-o', 'name')
    if (-not $stockflowFound) { Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'create', 'namespace', $Name) }
}
function Install-StockFlowDependency {
    param([string]$Release, [string]$Chart, [string]$Version, [string]$Namespace, [string[]]$Values)
    Ensure-StockFlowNamespace $Namespace
    $stockflowArguments = @('upgrade', '--install', $Release, $Chart, '--version', $Version, '--namespace', $Namespace, '--kube-context', $Context, '--wait', '--wait-for-jobs', '--timeout', '10m', '--history-max', '3')
    foreach ($stockflowValue in $Values) { $stockflowArguments += @('--values', $stockflowValue) }
    Invoke-StockFlowTool 'helm' $stockflowArguments
}

if ($Local) {
    if ($Context -ne 'kind-stockflow-smoke') { throw 'Local mode is restricted to the isolated kind-stockflow-smoke context.' }
    $env:KUBECONFIG = Join-Path $stockflowRoot '.logs\kind.kubeconfig'
} else {
    $env:AWS_PROFILE = 'stockflow'
    $stockflowInfraJson = Invoke-StockFlowTool 'terraform' @("-chdir=$(Join-Path $stockflowRoot 'terraform')", 'output', '-json')
    $stockflowInfra = ($stockflowInfraJson -join "`n") | ConvertFrom-Json
    if ($stockflowInfra.region.value -ne 'ap-southeast-2') { throw 'Terraform outputs must target Sydney.' }
    $stockflowKube = (Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'config', 'view', '--minify', '-o', 'json')) -join "`n" | ConvertFrom-Json
    if ($stockflowKube.clusters[0].cluster.server -ne $stockflowInfra.cluster_endpoint.value) {
        throw 'Kubernetes context does not match the applied Terraform endpoint.'
    }
    Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'apply', '-f', (Join-Path $stockflowRoot 'k8s\namespace.yaml'))
    Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'apply', '-f', (Join-Path $stockflowBootstrap 'gp3.yaml'))
}

Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'get', 'nodes', '-o', 'wide')
foreach ($stockflowRepo in @(
    @('eks', 'https://aws.github.io/eks-charts'),
    @('metrics-server', 'https://kubernetes-sigs.github.io/metrics-server/'),
    @('prometheus-community', 'https://prometheus-community.github.io/helm-charts'),
    @('argo', 'https://argoproj.github.io/argo-helm')
)) { Invoke-StockFlowTool 'helm' @('repo', 'add', $stockflowRepo[0], $stockflowRepo[1], '--force-update') }

if (-not $Local) {
    # IAM already belongs to Terraform. Helm creates only the annotated service account.
    $stockflowLbcVersion = $stockflowVersions.charts.loadBalancerController.version
    $stockflowCrdFile = Join-Path $stockflowGenerated 'lbc-crds.yaml'
    $stockflowCrds = Invoke-StockFlowTool 'helm' @('show', 'crds', 'eks/aws-load-balancer-controller', '--version', $stockflowLbcVersion)
    [System.IO.File]::WriteAllText($stockflowCrdFile, ($stockflowCrds -join "`n"), [System.Text.UTF8Encoding]::new($false))
    $stockflowGatewayFile = Join-Path $stockflowGenerated 'gateway-crds.yaml'
    Invoke-WebRequest -Uri $stockflowVersions.gatewayCrdUrl -OutFile $stockflowGatewayFile -UseBasicParsing -TimeoutSec 30
    if ((Get-FileHash -LiteralPath $stockflowGatewayFile -Algorithm SHA256).Hash -ne $stockflowVersions.gatewayCrdSha256) {
        throw 'Pinned Gateway CRD checksum mismatch.'
    }
    Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'apply', '--server-side', '-f', $stockflowGatewayFile)
    # The chart supplies the AWS-specific CRDs, including Gateway configurations.
    Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'apply', '--server-side', '-f', $stockflowCrdFile)
    $stockflowLbcValues = @{
        clusterName = $stockflowInfra.cluster_name.value
        region = $stockflowInfra.region.value
        vpcId = $stockflowInfra.vpc_id.value
        serviceAccount = @{ annotations = @{ 'eks.amazonaws.com/role-arn' = $stockflowInfra.load_balancer_controller_role_arn.value } }
    } | ConvertTo-Json -Depth 5
    $stockflowLbcFile = Join-Path $stockflowGenerated 'lbc-infrastructure.json'
    [System.IO.File]::WriteAllText($stockflowLbcFile, $stockflowLbcValues, [System.Text.UTF8Encoding]::new($false))
    Install-StockFlowDependency 'aws-load-balancer-controller' 'eks/aws-load-balancer-controller' $stockflowLbcVersion 'kube-system' @((Join-Path $stockflowBootstrap 'load-balancer-values.yaml'), $stockflowLbcFile)
}

$stockflowMetricsValues = @((Join-Path $stockflowBootstrap 'metrics-server-values.yaml'))
if ($Local) { $stockflowMetricsValues += (Join-Path $stockflowBootstrap 'metrics-server-local.yaml') }
Install-StockFlowDependency 'metrics-server' 'metrics-server/metrics-server' $stockflowVersions.charts.metricsServer.version 'kube-system' $stockflowMetricsValues
Install-StockFlowDependency 'monitoring' 'prometheus-community/kube-prometheus-stack' $stockflowVersions.charts.monitoring.version 'monitoring' @((Join-Path $stockflowBootstrap 'monitoring-values.yaml'))
Install-StockFlowDependency 'argocd' 'argo/argo-cd' $stockflowVersions.charts.argocd.version 'argocd' @((Join-Path $stockflowBootstrap 'argocd-values.yaml'))
Invoke-StockFlowTool 'kubectl' @('--context', $Context, 'top', 'nodes')
Write-Output 'Bootstrap releases are ready. Verify storage, scrape targets, pod capacity, and application health next.'
