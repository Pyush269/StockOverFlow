"""Report workload requests and conservative headroom for one demo worker."""
import argparse
import json
import subprocess
from decimal import Decimal
from pathlib import Path


def cpu(value):
    text = str(value or "0")
    return Decimal(text[:-1]) if text.endswith("m") else Decimal(text) * 1000


def memory(value):
    text = str(value or "0")
    for suffix, factor in [("Gi", 1024), ("Mi", 1), ("Ki", Decimal(1) / 1024), ("G", Decimal(10) ** 9 / 1024**2), ("M", Decimal(10) ** 6 / 1024**2)]:
        if text.endswith(suffix):
            return Decimal(text[:-len(suffix)]) * factor
    return Decimal(text) / 1024**2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--cpu-budget-millicores", type=int, default=1900)
    parser.add_argument("--memory-budget-mib", type=int, default=6800)
    parser.add_argument("--pod-budget", type=int, default=29)
    parser.add_argument("--reserve-cpu-millicores", type=int, default=0)
    parser.add_argument("--reserve-memory-mib", type=int, default=0)
    parser.add_argument("--reserve-pods", type=int, default=0)
    args = parser.parse_args()
    command = ["kubectl", "--context", args.context]
    pods = json.loads(subprocess.check_output(command + ["get", "pods", "-A", "-o", "json"], text=True))["items"]
    selected = [p for p in pods if p["spec"].get("nodeName") == args.node and p.get("status", {}).get("phase") not in ["Succeeded", "Failed"]]
    total_cpu = Decimal(args.reserve_cpu_millicores)
    total_memory = Decimal(args.reserve_memory_mib)
    unbounded = []
    for pod in selected:
        running = pod["spec"]["containers"]
        regular_cpu = sum(cpu(c.get("resources", {}).get("requests", {}).get("cpu")) for c in running)
        regular_memory = sum(memory(c.get("resources", {}).get("requests", {}).get("memory")) for c in running)
        sidecar_cpu = sidecar_memory = init_cpu = init_memory = Decimal(0)
        for init in pod["spec"].get("initContainers", []):
            init_request_cpu = cpu(init.get("resources", {}).get("requests", {}).get("cpu"))
            init_request_memory = memory(init.get("resources", {}).get("requests", {}).get("memory"))
            if init.get("restartPolicy") == "Always":
                sidecar_cpu += init_request_cpu
                sidecar_memory += init_request_memory
                init_cpu = max(init_cpu, sidecar_cpu)
                init_memory = max(init_memory, sidecar_memory)
            else:
                init_cpu = max(init_cpu, sidecar_cpu + init_request_cpu)
                init_memory = max(init_memory, sidecar_memory + init_request_memory)
        total_cpu += max(regular_cpu + sidecar_cpu, init_cpu) + cpu(pod["spec"].get("overhead", {}).get("cpu"))
        total_memory += max(regular_memory + sidecar_memory, init_memory) + memory(pod["spec"].get("overhead", {}).get("memory"))
        for container in running:
            if not all(key in container.get("resources", {}).get("requests", {}) for key in ["cpu", "memory"]):
                unbounded.append(pod["metadata"]["namespace"] + "/" + pod["metadata"]["name"] + ":" + container["name"])
    # Project an extra backend replica, simultaneous frontend/backend rollout surge, and a migration Job.
    reserve_cpu = Decimal(100 + 100 + 25 + 50)
    reserve_memory = Decimal(96 + 96 + 24 + 64)
    projected_cpu = total_cpu + reserve_cpu
    projected_memory = total_memory + reserve_memory
    projected_pods = len(selected) + args.reserve_pods + 4
    result = {
        "context": args.context, "node": args.node,
        "active_pods": len(selected), "reserved_missing_system_pods": args.reserve_pods,
        "baseline_cpu_requests_millicores": str(total_cpu), "baseline_memory_requests_mib": str(total_memory),
        "projected_cpu_requests_millicores": str(projected_cpu), "projected_memory_requests_mib": str(projected_memory),
        "projected_pods_with_hpa_rollout_migration": projected_pods,
        "budgets": {"cpu_millicores": args.cpu_budget_millicores, "memory_mib": args.memory_budget_mib, "pods": args.pod_budget},
        "containers_missing_request_fields": unbounded,
        "fits_requests_and_pod_budget": projected_cpu <= args.cpu_budget_millicores and projected_memory <= args.memory_budget_mib and projected_pods <= args.pod_budget,
        "limitation": "Requests/pod-count projection; not proof of peak usage or EKS scheduling/storage behavior. Verify actual allocatable values after deployment."
    }
    print(json.dumps(result, indent=2))
    out = Path(__file__).resolve().parents[1] / ".logs/kubernetes-capacity.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    if not result["fits_requests_and_pod_budget"]:
        raise SystemExit("The projected one-worker workload exceeds the configured budget")


if __name__ == "__main__":
    main()
