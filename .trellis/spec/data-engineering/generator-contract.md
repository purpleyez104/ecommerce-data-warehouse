# M2.4 Generator Contract

## 1. Scope / Trigger

本契约适用于 `generator/generate_ecommerce_oltp.py` 及其纯 Python 规则模块。它只生成候选 SQL 文本，不连接 MySQL、不修改 DDL，也不替代 T5 固定 Seed。业务语义以 `docs/spec.md` 和 `docs/milestone-2-business-design.md` 为准。

## 2. Signatures

```powershell
E:\Software\Python\3.12.10\python.exe -m generator.generate_ecommerce_oltp `
  --seed <non-negative-int> `
  --start-date <yyyy-MM-dd> `
  --days <positive-int> `
  --scale <positive-int> `
  --output <sql-path>
```

实现入口：

```python
build_sql(seed: int, start_date: date, days: int, scale: int) -> str
main(argv: list[str] | None = None) -> int
```

## 3. Contracts

- `seed` 必须为非负整数；相同的全部参数产生字节一致的 UTF-8、LF SQL。
- `start-date`、`days` 显式决定业务日期范围，禁止读取执行机器当前日期。
- `scale` 只控制候选数据规模；`scale=1` 是 T4 小型验收基线，不代表 Benchmark 规模。
- 输出按已确认的 19 表父子依赖顺序生成，且不向两个 `VIRTUAL GENERATED` 列赋值。
- SQL 写入前必须完成支付、退单/退款、优惠券、金额分摊及 Event/Session 身份等纯 Python 跨行校验。
- 静态检查最多证明产物为 `implemented`；MySQL 语法、约束和运行结果由 M2.5 验证。

## 4. Validation & Error Matrix

| 条件 | 预期行为 |
| --- | --- |
| seed 非整数或小于 0 | stderr 报错，退出状态非 0，不生成输出 |
| 日期不是合法 `yyyy-MM-dd` | stderr 报错，退出状态非 0，不生成输出 |
| days/scale 非整数或不大于 0 | stderr 报错，退出状态非 0，不生成输出 |
| 支付、退单/退款、优惠券、身份或金额规则违约 | 抛出 `RuleViolation`，CLI 返回 1，不生成输出 |
| 输出路径不可写 | stderr 报错，CLI 返回 1 |
| 参数与规则均合法 | CLI 返回 0，输出确定性候选 SQL |

## 5. Good / Base / Bad Cases

- Good：相同 seed、日期和规模连续生成两次，SHA-256 一致。
- Base：`--seed 42 --start-date 2025-01-29 --days 4 --scale 1` 生成 T4 小型规模的 19 表候选数据。
- Bad：负 seed、非法日期、零规模、跨表身份不一致、支付金额不守恒、累计退单/退款超限或优惠券越权均必须在写文件前失败。

## 6. Tests Required

- `tests/m2/test_generate_ecommerce_oltp.py`：断言确定性 checksum、显式日期、19 表顺序与字段 Contract、完整非法参数矩阵、规则违约非零且不写文件、跨表身份及实际支付/优惠券行校验。
- `tests/m2/test_generator_rules.py`：断言 `Decimal`/`HALF_UP`、正负尾差优先级、重复成功支付、退单状态数量、按明细累计退款和优惠券失败边界。
- T5 Contract：运行 `tests/m2/validate_fixed_seed_contract.ps1` 和 `tests/m2/test_validate_fixed_seed_contract.ps1`。
- 未经过 M2.5 时，不把上述测试描述为 MySQL Runtime Acceptance。

## 7. Wrong vs Correct

### Wrong

```python
business_date = date.today()
assert_payment_amount(payable, payable)
```

该写法依赖机器日期，并以同一变量自比较，无法发现实际支付行与订单应付金额不一致。

### Correct

```python
business_date = start_date + timedelta(days=offset)
assert_payment_amount(payment_row.payment_amount, order_row.payable_amount)
```

业务日期来自显式输入，跨行校验比较两个真实业务对象，并在 SQL 输出前失败。
