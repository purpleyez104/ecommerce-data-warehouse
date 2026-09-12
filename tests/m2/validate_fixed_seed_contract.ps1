param(
  [string]$ExpectedPath = (Join-Path $PSScriptRoot '..\..\mock\m2_fixed_seed_expected_results.json'),
  [string]$SeedPath = (Join-Path $PSScriptRoot '..\..\mysql\seed\001_ecommerce_oltp_fixed_seed.sql'),
  [string]$FailureCasesPath = (Join-Path $PSScriptRoot '..\..\mysql\seed\002_ecommerce_oltp_constraint_failure_cases.sql'),
  [string]$IdempotencyRunnerPath = (Join-Path $PSScriptRoot 'invoke_fixed_seed_idempotency.ps1')
)
$ErrorActionPreference = 'Stop'

function Get-InsertRows {
  param(
    [string]$Sql,
    [string]$Table
  )

  $pattern = '(?ms)^INSERT INTO `' + [regex]::Escape($Table) + '`.*?VALUES\r?\n(?<rows>.*?);'
  $match = [regex]::Match($Sql, $pattern)
  if (-not $match.Success) {
    throw "Missing INSERT block for $Table."
  }

  return @($match.Groups['rows'].Value -split "\r?\n" | Where-Object { $_ -match '^\s{2}\(' })
}

function Get-InsertColumns {
  param(
    [string]$Sql,
    [string]$Table
  )

  $pattern = '(?ms)^INSERT INTO `' + [regex]::Escape($Table) + '` \((?<columns>.*?)\) VALUES'
  $match = [regex]::Match($Sql, $pattern)
  if (-not $match.Success) { throw "Missing INSERT columns for $Table." }
  return @($match.Groups['columns'].Value.Split(',') | ForEach-Object { $_.Trim().Trim('`') })
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

function Get-SeedValue {
  param([string]$Value)

  $normalized = $Value.Trim()
  if ($normalized -eq 'NULL') { return $null }
  if ($normalized.StartsWith("'") -and $normalized.EndsWith("'")) {
    return $normalized.Substring(1, $normalized.Length - 2).Replace("''", "'")
  }
  return $normalized
}

$expected = Get-Content -LiteralPath $ExpectedPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($expected.table_counts.PSObject.Properties).Count -ne 19) { throw 'Expected 19 table counts.' }
if ($expected.business_dates.Count -ne 4) { throw 'Expected four business dates.' }
if (@($expected.table_business_keys.PSObject.Properties).Count -ne 19) { throw 'Expected business-key manifests for 19 tables.' }
if ($expected.scenario_mappings.Count -ne 12) { throw 'Expected twelve scenario mappings.' }
if ($expected.failure_cases.mysql_constraints.Count -ne 5 -or $expected.failure_cases.python_write_layer.Count -ne 9) { throw 'Expected 5 plus 9 failure cases.' }
if ($expected.rerun_contract -ne 'same-content-no-write; drift-nonzero') { throw 'Rerun contract differs.' }
if ($expected.content_digest.algorithm -ne 'SHA-256' -or $expected.content_digest.source -ne 'mysql/seed/001_ecommerce_oltp_fixed_seed.sql') {
  throw 'Expected-results content digest metadata differs.'
}

$requiredScenarioIds = 1..12 | ForEach-Object { 'M2-SC-{0:D3}' -f $_ }
$actualScenarioIds = @($expected.scenario_mappings | ForEach-Object { $_.id })
if (($actualScenarioIds -join ',') -ne ($requiredScenarioIds -join ',')) { throw 'Scenario IDs or ordering differ from M2-SC-001 through M2-SC-012.' }
$requiredDomains = @('user', 'traffic', 'product', 'transaction', 'marketing')
$actualDomains = @($expected.scenario_mappings.domains | Sort-Object -Unique)
foreach ($domain in $requiredDomains) {
  if ($domain -notin $actualDomains) { throw "Scenario mappings do not cover the $domain domain." }
}
$requiredInvariants = @(
  'unique-business-keys', 'referential-integrity', 'legal-status-combinations',
  'order-item-amount-conservation', 'payment-order-amount-conservation',
  'return-quantity-bound', 'refund-return-amount-conservation'
)
foreach ($invariant in $requiredInvariants) {
  if ($invariant -notin $expected.expected_invariants) { throw "Missing expected invariant: $invariant." }
}
$expectedFailureBehavior = @($expected.failure_cases.mysql_constraints | Where-Object { $_.expected -ne 'nonzero-rollback-no-baseline-change' }).Count -eq 0
$expectedPythonBehavior = @($expected.failure_cases.python_write_layer | Where-Object { $_.expected -ne 'nonzero-no-write' }).Count -eq 0
if (-not $expectedFailureBehavior -or -not $expectedPythonBehavior) { throw 'Failure cases must define non-zero and no-baseline-change behavior.' }

$seed = Get-Content -LiteralPath $SeedPath -Raw -Encoding UTF8
$failureCases = Get-Content -LiteralPath $FailureCasesPath -Raw -Encoding UTF8
$idempotencyRunner = Get-Content -LiteralPath $IdempotencyRunnerPath -Raw -Encoding UTF8
$tableOrder = @(
  'user_account', 'visitor', 'traffic_channel', 'brand', 'category', 'coupon', 'user_address', 'spu', 'sku',
  'visit_session', 'user_coupon', 'login_event', 'cart_event', 'page_view_event', 'sales_order',
  'sales_order_item', 'payment_attempt', 'return_order', 'refund_attempt'
)

$seedDigest = (Get-FileHash -LiteralPath $SeedPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($seedDigest -ne $expected.content_digest.sha256) { throw 'Normal fixed Seed SHA-256 differs from the expected-results manifest.' }
$parserProbe = @(Get-Fields "(1,'comma,value','escaped ''quote'''),")
if ($parserProbe.Count -ne 3 -or $parserProbe[1] -ne "'comma,value'" -or $parserProbe[2] -ne "'escaped ''quote'''" ) {
  throw 'Seed row parser does not preserve quoted commas and escaped quotes.'
}

if ($seed -notmatch '(?m)^START TRANSACTION;$' -or $seed -notmatch '(?m)^COMMIT;$') {
  throw 'Normal seed must use one transaction ending with COMMIT.'
}
if ($seed -match '(?im)^\s*SET\s+FOREIGN_KEY_CHECKS' -or $seed -match '(?m)^\s*ROLLBACK;$') {
  throw 'Normal seed must not disable foreign keys or roll back its legal data.'
}
if ($seed -match '2025-02-02') { throw 'Normal seed must stay within the four confirmed business dates.' }

$rowsByTable = @{}
$previousPosition = -1
foreach ($table in $tableOrder) {
  $position = $seed.IndexOf(('INSERT INTO `' + $table + '`'), [System.StringComparison]::Ordinal)
  if ($position -le $previousPosition) { throw "INSERT order is missing or invalid at $table." }
  $previousPosition = $position
  $rows = Get-InsertRows -Sql $seed -Table $table
  $rowsByTable[$table] = $rows
  if ($rows.Count -ne [int]$expected.table_counts.$table) {
    throw "Expected $($expected.table_counts.$table) $table rows; found $($rows.Count)."
  }
  $columns = Get-InsertColumns -Sql $seed -Table $table
  $businessKeys = [System.Collections.Generic.List[string]]::new()
  foreach ($row in $rows) {
    $fields = @(Get-Fields $row)
    if ($fields.Count -ne $columns.Count) { throw "Seed field count differs from the INSERT column count for $table." }
    $businessKeys.Add([string](Get-SeedValue $fields[1]))
  }
  if (($businessKeys | Sort-Object -Unique).Count -ne $businessKeys.Count) { throw "Duplicate business key found in $table." }
  $expectedBusinessKeys = @($expected.table_business_keys.$table)
  if (($businessKeys -join ',') -ne ($expectedBusinessKeys -join ',')) { throw "Business-key manifest differs for $table." }
}

$knownFailureIds = @($expected.failure_cases.mysql_constraints.id) + @($expected.failure_cases.python_write_layer.id)
$knownContracts = @('same-content-no-write', 'drift-nonzero')
foreach ($scenario in $expected.scenario_mappings) {
  if ($scenario.evidence.Count -eq 0) { throw "Scenario $($scenario.id) has no evidence mapping." }
  foreach ($evidence in $scenario.evidence) {
    $parts = @($evidence -split ':')
    if ($parts[0] -in $tableOrder) {
      if ($parts.Count -ne 2 -or $parts[1] -notin @($expected.table_business_keys.($parts[0]))) {
        throw "Scenario $($scenario.id) references an unknown business key: $evidence."
      }
    } elseif ($parts[0] -eq 'failure') {
      if ($parts.Count -ne 2 -or $parts[1] -notin $knownFailureIds) { throw "Scenario $($scenario.id) references an unknown failure case: $evidence." }
    } elseif ($parts[0] -eq 'contract') {
      if ($parts.Count -ne 2 -or $parts[1] -notin $knownContracts) { throw "Scenario $($scenario.id) references an unknown rerun contract: $evidence." }
    } elseif ($evidence -ne 'expected:zero-successful-payment-date:2025-02-01') {
      throw "Scenario $($scenario.id) contains unsupported evidence: $evidence."
    }
  }
}

$referenceDefinitions = @(
  @('user_address', 2, 'user_account'),
  @('category', 3, 'category'),
  @('spu', 3, 'brand'), @('spu', 4, 'category'), @('sku', 3, 'spu'),
  @('visit_session', 2, 'visitor'), @('visit_session', 3, 'traffic_channel'),
  @('user_coupon', 3, 'coupon'), @('user_coupon', 4, 'user_account'),
  @('login_event', 2, 'visitor'), @('login_event', 3, 'visit_session'), @('login_event', 4, 'user_account'),
  @('cart_event', 3, 'visitor'), @('cart_event', 4, 'visit_session'), @('cart_event', 5, 'user_account'), @('cart_event', 6, 'sku'),
  @('page_view_event', 2, 'visitor'), @('page_view_event', 3, 'visit_session'), @('page_view_event', 4, 'user_account'), @('page_view_event', 5, 'traffic_channel'), @('page_view_event', 8, 'sku'),
  @('sales_order', 3, 'user_account'), @('sales_order', 4, 'user_address'), @('sales_order', 5, 'user_coupon'),
  @('sales_order_item', 2, 'sales_order'), @('sales_order_item', 3, 'sku'),
  @('payment_attempt', 3, 'sales_order'),
  @('return_order', 3, 'sales_order'), @('return_order', 4, 'sales_order_item'),
  @('refund_attempt', 3, 'return_order'), @('refund_attempt', 4, 'sales_order'), @('refund_attempt', 5, 'payment_attempt')
)
$primaryKeysByTable = @{}
foreach ($table in $tableOrder) {
  $primaryKeysByTable[$table] = @(foreach ($row in $rowsByTable[$table]) { [string](Get-SeedValue (Get-Fields $row)[0]) })
}
foreach ($reference in $referenceDefinitions) {
  $childTable = $reference[0]
  $fieldIndex = [int]$reference[1]
  $parentTable = $reference[2]
  foreach ($row in $rowsByTable[$childTable]) {
    $value = Get-SeedValue (Get-Fields $row)[$fieldIndex]
    if ($null -ne $value -and [string]$value -notin $primaryKeysByTable[$parentTable]) {
      throw "$childTable contains an unresolved reference to $parentTable primary key $value."
    }
  }
}

$orders = @{}
foreach ($row in $rowsByTable['sales_order']) {
  $fields = Get-Fields $row
  $orderStatus = $fields[6].Trim("'")
  if ($orderStatus -notin @('CREATED', 'PAID', 'CANCELLED', 'PARTIALLY_REFUNDED', 'REFUNDED')) {
    throw "Invalid order status for $($fields[1])."
  }
  $hasCancellation = $fields[15] -ne 'NULL' -and $fields[16] -ne 'NULL'
  if (($orderStatus -eq 'CANCELLED') -ne $hasCancellation) { throw "Order cancellation fields differ for $($fields[1])." }
  $orders[[int]$fields[0]] = [pscustomobject]@{
    status = $orderStatus
    original = [decimal]$fields[9]
    productDiscount = [decimal]$fields[10]
    couponDiscount = [decimal]$fields[11]
    payable = [decimal]$fields[12]
  }
}

$itemTotals = @{}
$items = @{}
foreach ($row in $rowsByTable['sales_order_item']) {
  $fields = Get-Fields $row
  $itemPk = [int]$fields[0]
  $orderPk = [int]$fields[2]
  $quantity = [int]$fields[4]
  $unitOriginalPrice = [decimal]$fields[17]
  $originalAmount = [decimal]$fields[18]
  $productDiscount = [decimal]$fields[19]
  $couponDiscount = [decimal]$fields[20]
  $payableAmount = [decimal]$fields[21]
  if ($originalAmount -ne ($unitOriginalPrice * $quantity) -or $payableAmount -ne ($originalAmount - $productDiscount - $couponDiscount)) {
    throw "sales_order_item amount formula failed for $($fields[1])."
  }
  if (-not $itemTotals.ContainsKey($orderPk)) {
    $itemTotals[$orderPk] = [ordered]@{ original = [decimal]0; productDiscount = [decimal]0; couponDiscount = [decimal]0; payable = [decimal]0 }
  }
  $items[$itemPk] = [pscustomobject]@{ orderPk = $orderPk; quantity = $quantity }
  $itemTotals[$orderPk].original += $originalAmount
  $itemTotals[$orderPk].productDiscount += $productDiscount
  $itemTotals[$orderPk].couponDiscount += $couponDiscount
  $itemTotals[$orderPk].payable += $payableAmount
}
foreach ($orderPk in $orders.Keys) {
  if (-not $itemTotals.ContainsKey($orderPk)) { throw "Order $orderPk has no item total." }
  $order = $orders[$orderPk]
  $total = $itemTotals[$orderPk]
  if ($order.original -ne $total.original -or $order.productDiscount -ne $total.productDiscount -or $order.couponDiscount -ne $total.couponDiscount -or $order.payable -ne $total.payable) {
    throw "Order $orderPk does not reconcile to its items."
  }
}

$brandOne = Get-Fields $rowsByTable['brand'][0]
$itemOne = Get-Fields $rowsByTable['sales_order_item'][0]
if ((Get-SeedValue $brandOne[2]) -eq (Get-SeedValue $itemOne[6])) {
  throw 'M2-SC-010 requires a current product attribute to differ from the historical order snapshot.'
}

$paymentsByOrder = @{}
$payments = @{}
$paymentStatusCounts = @{}
foreach ($row in $rowsByTable['payment_attempt']) {
  $fields = Get-Fields $row
  $payment = [pscustomobject]@{ orderPk = [int]$fields[3]; status = $fields[4].Trim("'"); amount = [decimal]$fields[5] }
  if ($payment.status -notin @('CREATED', 'SUCCESS', 'FAILED')) { throw "Invalid payment status for $($fields[1])." }
  $payments[[int]$fields[0]] = $payment
  if (-not $paymentStatusCounts.ContainsKey($payment.status)) { $paymentStatusCounts[$payment.status] = 0 }
  $paymentStatusCounts[$payment.status]++
  if ($payment.status -eq 'SUCCESS') {
    if (-not $paymentsByOrder.ContainsKey($payment.orderPk)) { $paymentsByOrder[$payment.orderPk] = @() }
    $paymentsByOrder[$payment.orderPk] += $payment
  }
}
$successfulPaymentsOnZeroDenominatorDate = @($rowsByTable['payment_attempt'] | Where-Object {
  $fields = Get-Fields $_
  $fields[4].Trim("'") -eq 'SUCCESS' -and (Get-SeedValue $fields[8]).StartsWith('2025-02-01')
})
if ($successfulPaymentsOnZeroDenominatorDate.Count -ne 0) {
  throw 'M2-SC-011 requires 2025-02-01 to have no successful payment denominator.'
}
foreach ($orderPk in $orders.Keys) {
  $successfulPayments = if ($paymentsByOrder.ContainsKey($orderPk)) { @($paymentsByOrder[$orderPk]) } else { @() }
  if ($orders[$orderPk].status -eq 'PAID') {
    if ($successfulPayments.Count -ne 1 -or $successfulPayments[0].amount -ne $orders[$orderPk].payable) {
      throw "Paid order $orderPk requires one successful payment matching payable amount."
    }
  } elseif ($successfulPayments.Count -ne 0) {
    throw "Non-paid order $orderPk must not have a successful payment."
  }
}
if ($paymentStatusCounts['SUCCESS'] -ne 5 -or $paymentStatusCounts['FAILED'] -ne 3 -or $paymentStatusCounts['CREATED'] -ne 2) {
  throw 'Payment status coverage differs from the fixed seed.'
}

$returns = @{}
$returnStatusCounts = @{}
$returnQuantityByItem = @{}
foreach ($row in $rowsByTable['return_order']) {
  $fields = Get-Fields $row
  $orderPk = [int]$fields[3]
  $itemPk = [int]$fields[4]
  $returnQuantity = [int]$fields[6]
  $returnStatus = $fields[5].Trim("'")
  if (-not $items.ContainsKey($itemPk) -or $items[$itemPk].orderPk -ne $orderPk -or $returnQuantity -gt $items[$itemPk].quantity) {
    throw "Return $($fields[1]) does not match its order item."
  }
  if ($returnStatus -notin @('APPLIED', 'APPROVED', 'REJECTED', 'COMPLETED')) { throw "Invalid return status for $($fields[1])." }
  if (-not $returnStatusCounts.ContainsKey($returnStatus)) { $returnStatusCounts[$returnStatus] = 0 }
  $returnStatusCounts[$returnStatus]++
  if ($returnStatus -in @('APPLIED', 'APPROVED', 'COMPLETED')) {
    if (-not $returnQuantityByItem.ContainsKey($itemPk)) { $returnQuantityByItem[$itemPk] = 0 }
    $returnQuantityByItem[$itemPk] += $returnQuantity
  }
  $returns[[int]$fields[0]] = [pscustomobject]@{ orderPk = $orderPk; status = $returnStatus; refundAmount = if ($fields[8] -eq 'NULL') { $null } else { [decimal]$fields[8] } }
}
foreach ($itemPk in $returnQuantityByItem.Keys) {
  if ($returnQuantityByItem[$itemPk] -gt $items[$itemPk].quantity) { throw "Cumulative return quantity exceeds item $itemPk quantity." }
}
if ($returnStatusCounts['COMPLETED'] -ne 2 -or $returnStatusCounts['APPROVED'] -ne 1 -or $returnStatusCounts['REJECTED'] -ne 1) {
  throw 'Return status coverage differs from the fixed seed.'
}
$successfulRefundsByReturn = @{}
$successfulRefundsByPayment = @{}
$refundStatusCounts = @{}
foreach ($row in $rowsByTable['refund_attempt']) {
  $fields = Get-Fields $row
  $returnPk = [int]$fields[3]
  $paymentPk = [int]$fields[5]
  if (-not $returns.ContainsKey($returnPk) -or -not $payments.ContainsKey($paymentPk)) { throw "Refund $($fields[1]) has an unresolved parent." }
  if ([int]$fields[4] -ne $returns[$returnPk].orderPk -or [int]$fields[4] -ne $payments[$paymentPk].orderPk) { throw "Refund $($fields[1]) has inconsistent order references." }
  $refundStatus = $fields[6].Trim("'")
  if ($refundStatus -notin @('CREATED', 'SUCCESS', 'FAILED')) { throw "Invalid refund status for $($fields[1])." }
  if (-not $refundStatusCounts.ContainsKey($refundStatus)) { $refundStatusCounts[$refundStatus] = 0 }
  $refundStatusCounts[$refundStatus]++
  if ($refundStatus -eq 'SUCCESS') {
    if (-not $successfulRefundsByReturn.ContainsKey($returnPk)) { $successfulRefundsByReturn[$returnPk] = @() }
    $successfulRefundsByReturn[$returnPk] += [decimal]$fields[7]
    if (-not $successfulRefundsByPayment.ContainsKey($paymentPk)) { $successfulRefundsByPayment[$paymentPk] = [decimal]0 }
    $successfulRefundsByPayment[$paymentPk] += [decimal]$fields[7]
  }
}
if ($refundStatusCounts['SUCCESS'] -ne 2 -or $refundStatusCounts['FAILED'] -ne 2 -or $refundStatusCounts['CREATED'] -ne 1) {
  throw 'Refund status coverage differs from the fixed seed.'
}
foreach ($returnPk in $returns.Keys) {
  $return = $returns[$returnPk]
  $successfulRefunds = if ($successfulRefundsByReturn.ContainsKey($returnPk)) { @($successfulRefundsByReturn[$returnPk]) } else { @() }
  if ($return.status -eq 'COMPLETED') {
    if ($successfulRefunds.Count -ne 1 -or $successfulRefunds[0] -ne $return.refundAmount) {
      throw "Completed return $returnPk requires one successful refund matching its amount."
    }
  } elseif ($successfulRefunds.Count -ne 0) {
    throw "Non-completed return $returnPk must not have a successful refund."
  }
}
foreach ($paymentPk in $successfulRefundsByPayment.Keys) {
  if ($successfulRefundsByPayment[$paymentPk] -gt $payments[$paymentPk].amount) {
    throw "Cumulative successful refunds exceed payment $paymentPk amount."
  }
}

if (([regex]::Matches($failureCases, '(?m)^START TRANSACTION;$')).Count -ne 5 -or ([regex]::Matches($failureCases, '(?m)^ROLLBACK;$')).Count -ne 5 -or $failureCases -match '(?m)^COMMIT;$') {
  throw 'Constraint failures must consist of five isolated rollback transactions.'
}
if ($failureCases -notmatch "'PAY-BAD'.*1,'SUCCESS',45\.00") {
  throw 'Generated-column failure case must conflict with the existing successful payment for order 1.'
}
foreach ($requiredFailurePattern in @("'USR-001'", "VALUES \(99,NULL,'Missing code'", "'SKU-BAD'.*'USD'", "'ADDR-BAD',999", "'PAY-BAD'.*1,'SUCCESS',45\.00")) {
  if ($failureCases -notmatch $requiredFailurePattern) { throw "Missing required MySQL constraint-failure case: $requiredFailurePattern" }
}
if ($idempotencyRunner -match '(?i)\bUPDATE\s+[`$A-Za-z_]|\bREPLACE\s+[`$A-Za-z_]|\bINSERT\s+IGNORE\b|\bDELETE\s+FROM\b') {
  throw 'Idempotency runner must not mutate an existing baseline.'
}
foreach ($requiredRunnerPattern in @('ConfirmIsolatedDatabase', 'information_schema\.columns', 'Get-Sha256', 'Existing content for', 'allEmpty')) {
  if ($idempotencyRunner -notmatch $requiredRunnerPattern) { throw "Idempotency runner is missing $requiredRunnerPattern." }
}

Write-Output 'PASS: fixed-seed expected-results and SQL contract'
