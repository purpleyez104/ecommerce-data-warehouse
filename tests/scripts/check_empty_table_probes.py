#!/usr/bin/env python3
"""从 stdin 验证两张原空表的探针 INSERT/DELETE；避免打印业务数据。"""
import argparse,json,sys
from collections import Counter
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--op',choices=['c','d'],required=True)
a=p.parse_args()
expected={'biz_cart_merge_record':('merge_id','900000021'), 'biz_identity_mapping':('mapping_id','900000022')}
seen=Counter();issues=[]
for line in sys.stdin:
    try: raw=json.loads(line);e=raw.get('payload') or raw
    except (ValueError,TypeError):issues.append('parse');continue
    table=(e.get('source') or {}).get('table')
    if table not in expected:issues.append('table');continue
    field,key=expected[table];record=e.get('after') if a.op=='c' else e.get('before')
    if not isinstance(record,dict) or str(record.get(field))!=key or e.get('op')!=a.op:
        issues.append('record');continue
    if a.op=='d' and e.get('after') is not None:issues.append('after');continue
    seen[table]+=1
ok=not issues and sum(seen.values())==2 and all(seen[t]==1 for t in expected)
print('empty_table_probe',a.op,'2/2 PASS' if ok else 'NOT PASS')
sys.exit(0 if ok else 1)
