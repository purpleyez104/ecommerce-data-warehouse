# T6 M2.4 实施计划

## Planned Files

- `generator/generate_ecommerce_oltp.py`：标准库 CLI、参数解析、内存数据构造与 SQL 渲染。
- `generator/rules.py`：金额分摊、状态、支付、退单/退款和优惠券纯函数规则。
- `generator/README.md`：命令、固定输入、输出位置、预期退出状态、限制与回滚说明。
- `tests/m2/test_generator_rules.py`：`unittest` 规则与异常边界测试。
- `tests/m2/test_generate_ecommerce_oltp.py`：CLI 确定性、非法参数、跨日与 SQL 输出静态契约测试。

T5 的 `mysql/seed/`、`mock/` 与既有 `tests/m2/` 文件为只读输入，不属于 T6 修改范围。

## Execution Order

1. 建立纯规则函数与 `Decimal`、状态、退款和优惠券异常测试。
2. 实现显式参数 CLI 和确定性内存数据生成。
3. 以固定父子顺序渲染 SQL，保证不包含数据库连接或当前日期推断。
4. 添加 CLI 与输出 checksum 测试，并以 T5 预期 JSON 的日期、表清单和规则边界进行只读交叉核对。
5. 运行 Python `unittest`、T5 既有静态 Contract 和 `git diff --check`；不运行 MySQL。

## Verification Commands

```powershell
E:\Software\Python\3.12.10\python.exe -m unittest discover -s tests\m2 -p "test_*.py"
pwsh -NoProfile -File tests\m2\validate_fixed_seed_contract.ps1
pwsh -NoProfile -File tests\m2\test_validate_fixed_seed_contract.ps1
git diff --check
```

## Review Gates

- `scale=1` 与 `2025-01-29`、4 个业务日期的输出遵守 T4 规模和 T5 已确认规则边界。
- 相同 CLI 参数的两个输出 checksum 相同；非法日期、零或负 `days`/`scale`、非法 seed 和规则违约均非零退出。
- 不产生 MySQL 连接、DDL、T5 文件改动或性能结论。
