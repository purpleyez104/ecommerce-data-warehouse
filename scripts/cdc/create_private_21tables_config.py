#!/usr/bin/env python3
"""从已有的私密已验收 CDC YAML 生成独立 21 表配置，绝不回显密码/覆盖文件。需 PyYAML。"""
import argparse, json, os
from pathlib import Path
import yaml

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,help='已通过验证的本地私密 YAML')
    p.add_argument('--output',required=True,help='新的本地私密 YAML 路径；已存在时拒绝覆盖')
    p.add_argument('--server-id',default='5701-5704')
    p.add_argument('--topic',default='cdc_m2_21tables_acceptance')
    a=p.parse_args()
    source=Path(a.source);out=Path(a.output)
    if not source.is_file() or out.exists():p.error('源配置不存在或目标文件已存在；未做修改')
    contract=Path(__file__).resolve().parents[2]/'mock/generator/ecommerce_generator_v1/src/ecommerce_generator/schema_contract.json'
    table_names=sorted(json.loads(contract.read_text(encoding='utf-8')))
    if len(table_names)!=21:p.error('不是 21 张表，停止')
    data=yaml.safe_load(source.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or not isinstance(data.get('source'),dict) or not isinstance(data.get('sink'),dict):p.error('YAML 结构错误')
    if not data['source'].get('password'):p.error('源配置中未设置密码')
    if not isinstance(data['sink'].get('properties.bootstrap.servers'),str):p.error('Kafka 地址类型错误')
    data['source'].pop('database-name',None)
    data['source']['tables']=','.join('ecommerce_oltp_m2_acceptance.'+x for x in table_names)
    data['source']['scan.startup.mode']='initial'
    data['source']['server-id']=str(a.server_id)
    data['sink']['name']='M2 21 Tables Acceptance Sink'
    data['sink']['topic']=a.topic
    data['sink']['value.format']='debezium-json'
    data.setdefault('pipeline',{})['name']='m2-21tables-cdc-acceptance'
    data['pipeline']['parallelism']=1
    out.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f: yaml.safe_dump(data,f,allow_unicode=True,sort_keys=False)
    print('PASS: 私密配置生成；tables=21；权限=0600；密码未输出')
    print('path:',out)

if __name__=='__main__':main()
