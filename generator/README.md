# M2.4 Candidate Generator

`generate_ecommerce_oltp.py` uses only the Python standard library. It creates deterministic candidate `INSERT` SQL and never opens a MySQL connection.

Run from the repository root:

```powershell
E:\Software\Python\3.12.10\python.exe -m generator.generate_ecommerce_oltp --seed 42 --start-date 2025-01-29 --days 4 --scale 1 --output .\tmp\ecommerce_oltp_generated.sql
```

`--seed` is a non-negative integer; `--start-date` is `yyyy-MM-dd`; `--days` and `--scale` are positive integers. `scale=1` is the small T4 acceptance baseline, not a Benchmark size. The command exits nonzero for invalid parameters or a pure Python business-rule violation.

The output is UTF-8 with LF endings and is candidate input only. Do not execute it before the M1 MySQL gate and T7/M2.5. T5 fixed Seed files are read-only cross-check inputs; this generator does not replace them.

Run T6 static tests:

```powershell
E:\Software\Python\3.12.10\python.exe -m unittest discover -s tests\m2 -p "test_*.py"
```
