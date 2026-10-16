"""Create an isolated kubeconfig for the applied StockFlow EKS cluster."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import boto3
from botocore.config import Config
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='stockflow')
    args = parser.parse_args()
    outputs = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform'), 'output', '-json'], text=True))
    region = outputs['region']['value']
    name = outputs['cluster_name']['value']
    if region != 'ap-southeast-2' or name != 'stockflow-eks':
        raise RuntimeError('Terraform outputs must identify the reviewed Sydney StockFlow cluster')
    session = boto3.Session(profile_name=args.profile, region_name=region)
    client = session.client('eks', config=Config(connect_timeout=8, read_timeout=20, retries={'total_max_attempts': 3, 'mode': 'standard'}))
    cluster = client.describe_cluster(name=name)['cluster']
    if cluster['status'] != 'ACTIVE' or cluster['endpoint'] != outputs['cluster_endpoint']['value']:
        raise RuntimeError('The active AWS cluster does not match the applied Terraform endpoint')
    context = 'stockflow-eks-sydney'
    config = {'apiVersion':'v1','kind':'Config','clusters':[{'name':context,'cluster':{'server':cluster['endpoint'],'certificate-authority-data':cluster['certificateAuthority']['data']}}], 'contexts':[{'name':context,'context':{'cluster':context,'user':context}}], 'current-context':context, 'users':[{'name':context,'user':{'exec':{'apiVersion':'client.authentication.k8s.io/v1beta1','command':'aws','args':['eks','get-token','--cluster-name',name,'--region',region,'--profile',args.profile],'interactiveMode':'Never','provideClusterInfo':False}}}]}
    destination = ROOT / '.logs/eks.kubeconfig'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')
    print(f'Created {destination}; context {context}. Existing minikube/kind configuration was not changed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
