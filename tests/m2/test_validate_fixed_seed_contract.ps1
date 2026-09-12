$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$validatorPath = Join-Path $PSScriptRoot 'validate_fixed_seed_contract.ps1'
$idempotencyRunnerPath = Join-Path $PSScriptRoot 'invoke_fixed_seed_idempotency.ps1'
$seedPath = Join-Path $repositoryRoot 'mysql\seed\001_ecommerce_oltp_fixed_seed.sql'
$expectedPath = Join-Path $repositoryRoot 'mock\m2_fixed_seed_expected_results.json'

function Write-ExpectedForSeed {
  param(
    [string]$SourceExpectedPath,
    [string]$TargetExpectedPath,
    [string]$TargetSeedPath
  )

  $expected = Get-Content -LiteralPath $SourceExpectedPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $expected.content_digest.sha256 = (Get-FileHash -LiteralPath $TargetSeedPath -Algorithm SHA256).Hash.ToLowerInvariant()
  [System.IO.File]::WriteAllText(
    $TargetExpectedPath,
    ($expected | ConvertTo-Json -Depth 20) + "`n",
    [System.Text.UTF8Encoding]::new($false)
  )
}

function Assert-ValidationFailure {
  param(
    [string]$MutationName,
    [string]$MutatedSeedPath,
    [string]$MutatedExpectedPath
  )

  & pwsh -NoProfile -File $validatorPath -SeedPath $MutatedSeedPath -ExpectedPath $MutatedExpectedPath *> $null
  if ($LASTEXITCODE -eq 0) { throw "$MutationName unexpectedly passed the fixed-seed Contract." }
}

& $validatorPath
if (-not $?) { throw 'Baseline fixed-seed Contract must pass.' }
& pwsh -NoProfile -File $idempotencyRunnerPath -Server 'parser-only' -Port 1 -Database 'parser_only' -User 'parser_only' -ValidateParserOnly
if ($LASTEXITCODE -ne 0) { throw 'Idempotency runner parser regression must pass.' }

$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("m2-fixed-seed-contract-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporaryDirectory -ErrorAction Stop | Out-Null
try {
  $mutatedExpectedPath = Join-Path $temporaryDirectory 'm2_fixed_seed_expected_results.json'

  $amountSeedPath = Join-Path $temporaryDirectory 'amount_seed.sql'
  $amountSeed = (Get-Content -LiteralPath $seedPath -Raw -Encoding UTF8).Replace('5.45,24.55', '5.45,24.54')
  [System.IO.File]::WriteAllText($amountSeedPath, $amountSeed, [System.Text.UTF8Encoding]::new($false))
  Write-ExpectedForSeed -SourceExpectedPath $expectedPath -TargetExpectedPath $mutatedExpectedPath -TargetSeedPath $amountSeedPath
  Assert-ValidationFailure -MutationName 'Mutated item amount' -MutatedSeedPath $amountSeedPath -MutatedExpectedPath $mutatedExpectedPath

  $referenceSeedPath = Join-Path $temporaryDirectory 'reference_seed.sql'
  $referenceSeed = (Get-Content -LiteralPath $seedPath -Raw -Encoding UTF8).Replace("(4,'ADDR-004',4,", "(4,'ADDR-004',999,")
  [System.IO.File]::WriteAllText($referenceSeedPath, $referenceSeed, [System.Text.UTF8Encoding]::new($false))
  Write-ExpectedForSeed -SourceExpectedPath $expectedPath -TargetExpectedPath $mutatedExpectedPath -TargetSeedPath $referenceSeedPath
  Assert-ValidationFailure -MutationName 'Unresolved foreign key' -MutatedSeedPath $referenceSeedPath -MutatedExpectedPath $mutatedExpectedPath

  $duplicateKeySeedPath = Join-Path $temporaryDirectory 'duplicate_key_seed.sql'
  $duplicateKeySeed = (Get-Content -LiteralPath $seedPath -Raw -Encoding UTF8).Replace("(4,'USR-004',", "(4,'USR-001',")
  [System.IO.File]::WriteAllText($duplicateKeySeedPath, $duplicateKeySeed, [System.Text.UTF8Encoding]::new($false))
  Write-ExpectedForSeed -SourceExpectedPath $expectedPath -TargetExpectedPath $mutatedExpectedPath -TargetSeedPath $duplicateKeySeedPath
  Assert-ValidationFailure -MutationName 'Duplicate business key' -MutatedSeedPath $duplicateKeySeedPath -MutatedExpectedPath $mutatedExpectedPath

  $scenarioExpected = Get-Content -LiteralPath $expectedPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $scenarioExpected.scenario_mappings[11].id = 'M2-SC-999'
  [System.IO.File]::WriteAllText(
    $mutatedExpectedPath,
    ($scenarioExpected | ConvertTo-Json -Depth 20) + "`n",
    [System.Text.UTF8Encoding]::new($false)
  )
  Assert-ValidationFailure -MutationName 'Invalid scenario mapping' -MutatedSeedPath $seedPath -MutatedExpectedPath $mutatedExpectedPath
} finally {
  Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output 'PASS: fixed-seed Contract mutation regression'
