"""Read-only verification of the applied StockFlow AWS resources and public routing."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--infrastructure-only', action='store_true')
    args = parser.parse_args()
    outputs = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform'), 'output', '-json'], text=True))
    region, name = outputs['region']['value'], outputs['cluster_name']['value']
    if region != 'ap-southeast-2' or name != 'stockflow-eks':
        raise RuntimeError('Expected the reviewed Sydney StockFlow deployment')
    session = boto3.Session(profile_name='stockflow', region_name=region)
    config = Config(connect_timeout=8, read_timeout=30, retries={'total_max_attempts': 3, 'mode': 'standard'})
    clients = {service: session.client(service, config=config) for service in ['sts', 'eks', 'ec2', 'elbv2']}
    if clients['sts'].get_caller_identity()['Account'] != '181185361204':
        raise RuntimeError('Unexpected AWS project')
    cluster = clients['eks'].describe_cluster(name=name)['cluster']
    assert cluster['status'] == 'ACTIVE' and cluster['endpoint'] == outputs['cluster_endpoint']['value']
    groups = [g for page in clients['eks'].get_paginator('list_nodegroups').paginate(clusterName=name) for g in page['nodegroups']]
    assert groups == ['stockflow-eks-capstone-workers']
    group = clients['eks'].describe_nodegroup(clusterName=name, nodegroupName=groups[0])['nodegroup']
    assert group['status'] == 'ACTIVE' and group['scalingConfig']['desiredSize'] == 1 and not group['health']['issues']
    kube = ['kubectl', '--context', 'stockflow-eks-sydney']

    def get(tail):
        return json.loads(subprocess.check_output(kube + tail, text=True, timeout=60))

    kubeconfig = get(['config', 'view', '--minify', '-o', 'json'])
    assert kubeconfig['clusters'][0]['cluster']['server'] == cluster['endpoint']
    nodes = get(['get', 'nodes', '-o', 'json'])['items']
    assert len(nodes) == 1 and any(c['type'] == 'Ready' and c['status'] == 'True' for c in nodes[0]['status']['conditions'])
    instance_id = nodes[0]['spec']['providerID'].rsplit('/', 1)[1]
    instance = clients['ec2'].describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
    assert instance['State']['Name'] == 'running' and not instance.get('PublicIpAddress')
    assert instance['SubnetId'] in outputs['private_subnet_ids']['value'] and instance['VpcId'] == outputs['vpc_id']['value']
    assert instance['MetadataOptions']['HttpTokens'] == 'required' and instance['MetadataOptions']['HttpPutResponseHopLimit'] == 1
    root_ids = [v['Ebs']['VolumeId'] for v in instance['BlockDeviceMappings']]
    root_volumes = clients['ec2'].describe_volumes(VolumeIds=root_ids)['Volumes']
    assert all(v['Encrypted'] and v['VolumeType'] == 'gp3' for v in root_volumes)
    addons = {}
    for page in clients['eks'].get_paginator('list_addons').paginate(clusterName=name):
        for addon_name in page['addons']:
            addon = clients['eks'].describe_addon(clusterName=name, addonName=addon_name)['addon']
            assert addon['status'] == 'ACTIVE' and not addon['health']['issues'], addon_name
            addons[addon_name] = {'status': addon['status'], 'version': addon['addonVersion']}
    assert set(addons) == {'vpc-cni', 'coredns', 'kube-proxy', 'aws-ebs-csi-driver', 'eks-pod-identity-agent'}
    associations = [a for page in clients['eks'].get_paginator('list_pod_identity_associations').paginate(clusterName=name) for a in page['associations']]
    assert {a['serviceAccount'] for a in associations} == {'aws-node', 'ebs-csi-controller-sa', 'aws-load-balancer-controller'}
    result = {
        'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'region': region,
        'cluster': {'name': name, 'status': cluster['status'], 'version': cluster['version'], 'private_api': cluster['resourcesVpcConfig']['endpointPrivateAccess'], 'public_api_restricted_to_operator': all(c.endswith('/32') for c in cluster['resourcesVpcConfig']['publicAccessCidrs'])},
        'worker': {'count': 1, 'type': instance['InstanceType'], 'state': 'Ready', 'private_subnet': True, 'public_ip': False, 'imds_v2_required': True, 'metadata_hop_limit': 1, 'encrypted_gp3_root': True, 'allocatable': nodes[0]['status']['allocatable']},
        'addons': addons, 'pod_identity_service_accounts': sorted(a['serviceAccount'] for a in associations),
    }
    if not args.infrastructure_only:
        ingress = get(['-n', 'stockflow', 'get', 'ingress', '-o', 'json'])['items'][0]
        hostname = ingress['status']['loadBalancer']['ingress'][0]['hostname']
        balancers = [lb for page in clients['elbv2'].get_paginator('describe_load_balancers').paginate() for lb in page['LoadBalancers'] if lb['DNSName'] == hostname]
        assert len(balancers) == 1 and balancers[0]['VpcId'] == outputs['vpc_id']['value']
        lb = balancers[0]
        assert lb['State']['Code'] == 'active' and lb['Scheme'] == 'internet-facing' and lb['Type'] == 'application'
        tags = clients['elbv2'].describe_tags(ResourceArns=[lb['LoadBalancerArn']])['TagDescriptions'][0]['Tags']
        assert any(t['Key'] == 'elbv2.k8s.aws/cluster' and t['Value'] == name for t in tags)
        target_groups = [tg for page in clients['elbv2'].get_paginator('describe_target_groups').paginate(LoadBalancerArn=lb['LoadBalancerArn']) for tg in page['TargetGroups']]
        health = []
        for target_group in target_groups:
            targets = clients['elbv2'].describe_target_health(TargetGroupArn=target_group['TargetGroupArn'])['TargetHealthDescriptions']
            assert len(targets) >= 2 and all(t['TargetHealth']['State'] == 'healthy' for t in targets)
            health.append({'target_type': target_group['TargetType'], 'healthy_targets': len(targets)})
        assert len(health) == 2
        pvc = get(['-n', 'stockflow', 'get', 'pvc', '-o', 'json'])['items'][0]
        assert pvc['status']['phase'] == 'Bound' and pvc['spec']['storageClassName'] == 'gp3'
        pv = get(['get', 'pv', pvc['spec']['volumeName'], '-o', 'json'])
        volume = clients['ec2'].describe_volumes(VolumeIds=[pv['spec']['csi']['volumeHandle']])['Volumes'][0]
        assert volume['Encrypted'] and volume['VolumeType'] == 'gp3' and volume['State'] == 'in-use'
        assert any(a['InstanceId'] == instance_id for a in volume['Attachments'])
        result['application_storage'] = {'pvc': pvc['metadata']['name'], 'phase': 'Bound', 'type': 'gp3', 'size_gib': volume['Size'], 'encrypted': True, 'attached_to_worker': True}
        result['load_balancer'] = {'url': 'http://' + hostname, 'state': 'active', 'scheme': 'internet-facing', 'target_groups': health}
    destination = ROOT / '.logs' / ('aws-infrastructure-verification.json' if args.infrastructure_only else 'aws-verification.json')
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
