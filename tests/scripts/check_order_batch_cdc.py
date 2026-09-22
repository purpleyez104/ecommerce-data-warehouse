#!/usr/bin/env python3
"""从 stdin 核对单个 run-id 对应的订单 CDC；不推断其他表的事件已验收。"""
import argparse,json,sys
from collections import Counter
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--run-id',required=True)
p.add_argument('--orders',type=int,required=True)
p.add_argument('--paid',type=int,required=True)
p.add_argument('--canceled',type=int,required=True)
p.add_argument('--messages',type=int,default=None,help='可选：实际读取总消息数的精确核对')
a=p.parse_args()
prefix=f'GEN1_{a.run_id}_ORDER_';creates=Counter();latest={};total=0;parse_errors=0
for line in sys.stdin:
    total+=1
    try: raw=json.loads(line);e=raw.get('payload') or raw
    except (TypeError,ValueError):parse_errors+=1;continue
    if (e.get('source') or {}).get('table')!='biz_order':continue
    after=e.get('after')
    if not isinstance(after,dict) or not str(after.get('order_no','')).startswith(prefix):continue
    oid=str(after.get('order_id'));op=e.get('op')
    if op=='c':creates[oid]+=1
    if op in ('c','u'):latest[oid]=after.get('order_status')
states=Counter(latest.values())
ok=(parse_errors==0 and len(creates)==a.orders and all(n==1 for n in creates.values())
    and set(creates)==set(latest) and states==Counter({'PAID':a.paid,'CANCELED':a.canceled})
    and (a.messages is None or total==a.messages))
print('messages_checked:',total,'unique_order_inserts:',len(creates),'final_states:',dict(states))
print('ORDER_CDC:','PASS' if ok else 'NOT PASS')
sys.exit(0 if ok else 1)
