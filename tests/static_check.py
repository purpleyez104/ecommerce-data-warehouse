#!/usr/bin/env python3
"""Non-executing structural checks; NOT a MySQL parser or database acceptance test."""
import re
from pathlib import Path
p=Path(__file__).resolve().parents[1] / 'mysql/ddl/001_ecommerce_oltp_v1.sql'
s=p.read_text(encoding='utf-8')
code='\n'.join(x for x in s.splitlines() if not x.lstrip().startswith('--'))
names=re.findall(r'^CREATE TABLE `([^`]+)` \(',code, re.M)
expected=['biz_user','biz_visitor','biz_identity_mapping','biz_category','biz_spu','biz_sku','biz_product_change_event','biz_cart','biz_cart_item','biz_cart_merge_record','biz_coupon_template','biz_coupon','biz_order','biz_order_item','biz_order_status_event','biz_payment_attempt','biz_payment_event','biz_refund_request','biz_refund_transaction','biz_refund_event','biz_coupon_event']
assert names==expected, (len(names),names)
assert len(names)==len(set(names))==21
assert code.count('ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;')==21
assert len(re.findall(r'^  PRIMARY KEY \(',code,re.M))==21
fks=re.findall(r'CONSTRAINT `([^`]+)` FOREIGN KEY \(([^)]*)\)\s*REFERENCES `([^`]+)` \(([^)]*)\)',code)
cks=re.findall(r'CONSTRAINT `(ck_[^`]+)` CHECK \(',code)
uniques=re.findall(r'UNIQUE KEY `([^`]+)`',code)
idxs=re.findall(r'(?<!UNIQUE )KEY `([^`]+)`',code)
all_constr=[a for a,_,_,_ in fks]+cks
assert len(set(all_constr))==len(all_constr), 'Duplicate constraint symbols'
assert all(len(x)<=64 for x in all_constr+uniques+idxs), 'Identifier > 64 chars'
assert len(fks)>=20
for cname,child,parent,parcol in fks:
    assert parent in names, (cname, parent)
    assert len(re.findall(r'`[^`]+`',child)) == len(re.findall(r'`[^`]+`',parcol)), (cname,child,parcol)
    if cname not in ('fk_biz_coupon_locked_order','fk_biz_coupon_used_order'):
        # find the containing CREATE statement by preceding CREATE TABLE closest
        at=code.index('CONSTRAINT `'+cname+'` FOREIGN KEY')
        previous=[(code.index('CREATE TABLE `'+n+'`'),n) for n in names if code.index('CREATE TABLE `'+n+'`')<at]
        current=max(previous)[1]
        assert names.index(parent) <= names.index(current), (cname,current,parent)
assert len(re.findall(r'^ALTER TABLE ',code,re.M))==1
assert re.search(r'^ALTER TABLE `biz_coupon`',code,re.M)
assert not re.search(r'\b(DROP|TRUNCATE|DELETE|INSERT|UPDATE)\s+(?:TABLE|FROM|INTO|`)',code,re.I)
assert 'CREATE TABLE IF NOT EXISTS' not in code
assert 'password' not in code.lower()
assert re.search(r'^USE `ecommerce_oltp`;',code,re.M)
# Crude parenthesis scan without backtick awareness needed (no parentheses inside quoted strings in this DDL).
depth=0
for i,c in enumerate(code):
    if c=='(': depth+=1
    if c==')': depth-=1
    assert depth>=0, ('unbalanced',i)
assert depth==0
stmts=[x.strip() for x in code.split(';') if x.strip()]
assert len(stmts)==23, len(stmts)
assert stmts[0].startswith('USE ')
assert all(x.startswith('CREATE TABLE ') for x in stmts[1:-1])
assert stmts[-1].startswith('ALTER TABLE `biz_coupon`')
print('Structural static checks: PASS (no DB connection; no SQL executed)')
print('Tables:',len(names))
print('Primary keys:',len(re.findall(r'^  PRIMARY KEY \(',code,re.M)))
print('Foreign keys:',len(fks))
print('Check constraints:',len(cks))
print('Unique keys:',len(uniques))
print('DDL statements:',len(stmts))
print('Destructive DML/DDL: none found')
print('DDL bytes:',p.stat().st_size)
