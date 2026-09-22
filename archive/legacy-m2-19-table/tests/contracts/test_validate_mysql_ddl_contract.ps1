$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$checker = Join-Path $PSScriptRoot 'validate_mysql_ddl_contract.ps1'
$ddl = Join-Path $root 'mysql\ddl\001_ecommerce_oltp_candidate.sql'
$model = Join-Path $root 'docs\milestone-2-business-design.md'
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("t2-ddl-contract-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $temp | Out-Null
function Invoke-Case([string]$Name, [string]$Path, [int]$ExpectedExitCode) { & pwsh -NoProfile -File $checker -DdlPath $Path -ModelPath $model; if ($LASTEXITCODE -ne $ExpectedExitCode) { throw "$Name expected exit $ExpectedExitCode; got $LASTEXITCODE." }; Write-Output "PASS: $Name" }
function Write-Variant([string]$Name, [string]$Old, [string]$New) { $content = Get-Content -LiteralPath $ddl -Raw -Encoding UTF8; if (-not $content.Contains($Old)) { throw "Fixture replacement for $Name was not found." }; $path = Join-Path $temp "$Name.sql"; [System.IO.File]::WriteAllText($path, $content.Replace($Old, $New), [System.Text.UTF8Encoding]::new($false)); return $path }
try {
  Invoke-Case 'normal DDL' $ddl 0
  Invoke-Case 'missing input' (Join-Path $temp 'missing.sql') 1
  Invoke-Case 'wrong FK target' (Write-Variant 'wrong-fk' 'REFERENCES `visitor` (`visitor_pk`)' 'REFERENCES `user_account` (`user_account_pk`)') 1
  Invoke-Case 'wrong CHECK expression' (Write-Variant 'wrong-check' 'CONSTRAINT `ck_sku_currency` CHECK (`currency` = ''CNY'')' 'CONSTRAINT `ck_sku_currency` CHECK (`currency` = ''USD'')') 1
  Invoke-Case 'wrong rollback order' (Write-Variant 'wrong-rollback' 'refund_attempt, return_order' 'return_order, refund_attempt') 1
} finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force } }
