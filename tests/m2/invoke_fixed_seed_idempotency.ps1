param(
  [Parameter(Mandatory)]
  [string]$Server,
  [Parameter(Mandatory)]
  [int]$Port,
  [Parameter(Mandatory)]
  [string]$Database,
  [Parameter(Mandatory)]
  [string]$User,
  [switch]$ConfirmIsolatedDatabase,
  [switch]$ValidateParserOnly,
  [string]$MySqlPath = 'mysql',
  [string]$PasswordEnvironmentVariable = 'M2_TEST_MYSQL_PASSWORD',
  [string]$ExpectedPath = (Join-Path $PSScriptRoot '..\..\mock\m2_fixed_seed_expected_results.json'),
  [string]$SeedPath = (Join-Path $PSScriptRoot '..\..\mysql\seed\001_ecommerce_oltp_fixed_seed.sql')
)
$ErrorActionPreference = 'Stop'

function Get-InsertRows {
  param(
    [string]$Sql,
    [string]$Table
  )

  $pattern = '(?ms)^INSERT INTO `' + [regex]::Escape($Table) + '`.*?VALUES\r?\n(?<rows>.*?);'
  $match = [regex]::Match($Sql, $pattern)
  if (-not $match.Success) { throw "Missing INSERT block for $Table." }
  return @($match.Groups['rows'].Value -split "\r?\n" | Where-Object { $_ -match '^\s{2}\(' })
}

function Get-Fields {
  param([string]$Row)

  $value = $Row.Trim()
  if ($value.EndsWith(',') -or $value.EndsWith(';')) {
    $value = $value.Substring(0, $value.Length - 1).TrimEnd()
  }
  if (-not $value.StartsWith('(') -or -not $value.EndsWith(')')) {
    throw 'Seed row must be enclosed in parentheses.'
  }

  $value = $value.Substring(1, $value.Length - 2)
  $fields = [System.Collections.Generic.List[string]]::new()
  $field = [System.Text.StringBuilder]::new()
  $insideQuotedValue = $false
  for ($index = 0; $index -lt $value.Length; $index++) {
    $character = $value[$index]
    if ($character -eq [char]39) {
      [void]$field.Append($character)
      if ($insideQuotedValue -and $index + 1 -lt $value.Length -and $value[$index + 1] -eq [char]39) {
        [void]$field.Append($value[$index + 1])
        $index++
      } else {
        $insideQuotedValue = -not $insideQuotedValue
      }
    } elseif ($character -eq [char]44 -and -not $insideQuotedValue) {
      $fields.Add($field.ToString())
      [void]$field.Clear()
    } else {
      [void]$field.Append($character)
    }
  }
  if ($insideQuotedValue) { throw 'Seed row contains an unterminated quoted value.' }
  $fields.Add($field.ToString())
  return $fields.ToArray()
}

function Convert-SeedField {
  param([string]$Value)

  $normalized = $Value.Trim()
  if ($normalized -eq 'NULL') { return '<NULL>' }
  if ($normalized.StartsWith("'") -and $normalized.EndsWith("'")) {
    $normalized = $normalized.Substring(1, $normalized.Length - 2).Replace("''", "'")
  }
  if ($normalized -match '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$') {
    return $normalized + '000'
  }
  return $normalized
}

function Get-Sha256 {
  param([string[]]$Rows)

  $input = [Text.Encoding]::UTF8.GetBytes(($Rows -join "`n"))
  return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($input)).ToLowerInvariant()
}

if ($ValidateParserOnly) {
  $intermediateRow = @(Get-Fields "(1,'comma,value','escaped ''quote'''),")
  $finalRow = @(Get-Fields "(2,'final',NULL);")
  if ($intermediateRow.Count -ne 3 -or $intermediateRow[1] -ne "'comma,value'" -or $intermediateRow[2] -ne "'escaped ''quote'''" -or $finalRow.Count -ne 3) {
    throw 'Seed row parser self-test failed.'
  }
  Write-Output 'PASS: idempotency runner seed row parser'
  exit 0
}

if (-not $ConfirmIsolatedDatabase) {
  throw 'Pass -ConfirmIsolatedDatabase only after confirming the target is the dedicated T7 test database.'
}
if (-not (Test-Path -LiteralPath $ExpectedPath) -or -not (Test-Path -LiteralPath $SeedPath)) {
  throw 'Expected-results JSON or normal Seed SQL is missing.'
}
if (-not (Get-Command $MySqlPath -ErrorAction SilentlyContinue)) {
  throw "MySQL client '$MySqlPath' was not found."
}

$password = [Environment]::GetEnvironmentVariable($PasswordEnvironmentVariable, 'Process')
if ([string]::IsNullOrWhiteSpace($password)) {
  throw "Process environment variable $PasswordEnvironmentVariable is required."
}
$expected = Get-Content -LiteralPath $ExpectedPath -Raw -Encoding UTF8 | ConvertFrom-Json
$seed = Get-Content -LiteralPath $SeedPath -Raw -Encoding UTF8
$seedDigest = (Get-FileHash -LiteralPath $SeedPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expected.content_digest.algorithm -ne 'SHA-256' -or $seedDigest -ne $expected.content_digest.sha256) {
  throw 'Normal fixed Seed does not match the expected-results content digest.'
}
$tables = @($expected.table_counts.PSObject.Properties.Name)
if ($tables.Count -ne 19) { throw 'Expected-results JSON must define 19 tables.' }

$mysqlArguments = @('--batch', '--skip-column-names', '--raw', "--host=$Server", "--port=$Port", "--user=$User", "--database=$Database")
$previousMySqlPassword = [Environment]::GetEnvironmentVariable('MYSQL_PWD', 'Process')
[Environment]::SetEnvironmentVariable('MYSQL_PWD', $password, 'Process')
try {
  function Invoke-MySqlQuery {
    param([string]$Sql)

    $output = @(& $MySqlPath @mysqlArguments "--execute=$Sql")
    if ($LASTEXITCODE -ne 0) { throw 'MySQL query returned non-zero.' }
    return $output
  }

  $quotedTables = ($tables | ForEach-Object { "'$($_.Replace("'", "''"))'" }) -join ','
  $columnRows = Invoke-MySqlQuery @"
SELECT table_name, column_name, data_type, extra
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name IN ($quotedTables)
  AND extra NOT LIKE '%GENERATED%'
ORDER BY table_name, ordinal_position;
"@
  $columnsByTable = @{}
  foreach ($columnRow in $columnRows) {
    $parts = $columnRow -split "`t", 4
    if ($parts.Count -ne 4) { throw 'Unexpected information_schema column output.' }
    if (-not $columnsByTable.ContainsKey($parts[0])) { $columnsByTable[$parts[0]] = @() }
    $columnsByTable[$parts[0]] += [pscustomobject]@{ name = $parts[1]; dataType = $parts[2] }
  }

  $databaseCounts = @{}
  foreach ($table in $tables) {
    if (-not $columnsByTable.ContainsKey($table)) { throw "Target database does not contain $table." }
    $databaseCounts[$table] = [int](Invoke-MySqlQuery "SELECT COUNT(*) FROM `$table`;")
  }
  $allEmpty = @($databaseCounts.Values | Where-Object { $_ -ne 0 }).Count -eq 0

  if ($allEmpty) {
    $seed | & $MySqlPath @mysqlArguments
    if ($LASTEXITCODE -ne 0) { throw 'Normal fixed Seed returned non-zero.' }
    Write-Output 'INFO: normal fixed Seed inserted into the empty isolated test database.'
  }

  foreach ($table in $tables) {
    $expectedRows = Get-InsertRows -Sql $seed -Table $table
    $expectedCount = [int]$expected.table_counts.$table
    if ($expectedRows.Count -ne $expectedCount) { throw "Seed/JSON row-count mismatch for $table." }
    $columns = $columnsByTable[$table]
    $expectedCanonicalRows = foreach ($row in $expectedRows) {
      $fields = Get-Fields $row
      if ($fields.Count -ne $columns.Count) { throw "Seed field count does not match non-generated columns for $table." }
      (($fields | ForEach-Object { Convert-SeedField $_ }) -join [char]31)
    }
    $selectFields = foreach ($column in $columns) {
      $columnName = '`' + $column.name.Replace('`', '``') + '`'
      if ($column.dataType -in @('datetime', 'timestamp')) {
        "CASE WHEN $columnName IS NULL THEN '<NULL>' ELSE DATE_FORMAT($columnName, '%Y-%m-%d %H:%i:%s.%f') END"
      } else {
        "CASE WHEN $columnName IS NULL THEN '<NULL>' ELSE CAST($columnName AS CHAR) END"
      }
    }
    $primaryKey = '`' + $table + '_pk`'
    $actualRows = Invoke-MySqlQuery "SELECT CONCAT_WS(CHAR(31), $($selectFields -join ', ')) FROM `$table` ORDER BY $primaryKey;"
    if ($actualRows.Count -ne $expectedCount -or (Get-Sha256 $actualRows) -ne (Get-Sha256 $expectedCanonicalRows)) {
      throw "Existing content for $table differs from the fixed Seed; no write was performed."
    }
  }
} finally {
  [Environment]::SetEnvironmentVariable('MYSQL_PWD', $previousMySqlPassword, 'Process')
}

Write-Output 'PASS: isolated database matches the fixed Seed; no second write was performed.'
