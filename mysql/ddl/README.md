# Candidate MySQL DDL

`001_ecommerce_oltp_candidate.sql` is the M2.2 Candidate DDL for database `ecommerce_oltp`. Its evidence status is `implemented`; it has not been executed or verified on MySQL.

Run the static Contract check from the repository root:

```powershell
pwsh -File tests/contracts/validate_mysql_ddl_contract.ps1
pwsh -File tests/contracts/test_validate_mysql_ddl_contract.ps1
```

The checker reads the Candidate DDL and the confirmed M2.2 field/object registry. It exits `0` only when the 19-table / 230-field contract, names, FK child/parent tuples, key `CHECK` expressions, UQ/secondary-index columns, generated-column/unique pairings, and creation/rollback order match; any violation exits non-zero. The regression entry verifies the normal input plus missing input, wrong FK, wrong `CHECK`, and wrong rollback order. Neither command connects to MySQL or proves MySQL 8.0.46 syntax, constraint behavior, or index performance.

The SQL file is ordered for creation without disabling FK checks. A real execution and any `DROP TABLE` rollback remain blocked until T7 and must use an isolated MySQL test database following the inverse order documented in the SQL header.
