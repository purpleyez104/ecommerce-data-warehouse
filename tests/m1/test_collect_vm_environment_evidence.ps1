$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$scriptPath = Join-Path $repoRoot 'scripts\m1\collect-vm-environment-evidence.sh'
$readmePath = Join-Path $repoRoot 'scripts\m1\README.md'

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    throw "Missing script: $scriptPath"
}

$script = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8
$readme = Get-Content -LiteralPath $readmePath -Raw -Encoding UTF8
$failures = [System.Collections.Generic.List[string]]::new()

function Assert-Contains {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Message
    )
    if ($Text -notmatch $Pattern) {
        $failures.Add($Message)
    }
}

function Assert-NotContains {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Message
    )
    if ($Text -match $Pattern) {
        $failures.Add($Message)
    }
}

Assert-Contains $script '--run-id' 'Missing --run-id interface.'
Assert-Contains $script '--output-dir' 'Missing --output-dir interface.'
Assert-Contains $script '--max-clock-skew-seconds' 'Missing clock-skew threshold interface.'
Assert-Contains $script ([regex]::Escape('[A-Za-z0-9][A-Za-z0-9._-]{0,79}')) 'run-id validation is missing or changed.'
Assert-Contains $script '\$output_dir != / && \$output_dir != /data' 'Broad output-directory protection is missing.'
Assert-Contains $script '/data/logs/ecommerce-data-warehouse/m1/' 'M1 evidence-root restriction is missing.'
Assert-Contains $script 'output-dir already contains files' 'Non-empty output-directory protection is missing.'
Assert-Contains $script '\$\(id -un\) == yee' 'Execution-user protection is missing.'
Assert-Contains $script '\$\(hostname -s\) == hadoop201' 'Orchestrator-node protection is missing.'
Assert-Contains $script 'hadoop201 hadoop202 hadoop203' 'The three expected nodes are not declared.'
Assert-Contains $script 'identity-system' 'System identity evidence section is missing.'
Assert-Contains $script 'network-time' 'Network/time evidence section is missing.'
Assert-Contains $script 'storage' 'Storage evidence section is missing.'
Assert-Contains $script 'limits-runtime' 'Runtime evidence section is missing.'
Assert-Contains $script 'process-ports' 'Process/port evidence section is missing.'
Assert-Contains $script 'component-inventory' 'Component inventory section is missing.'
Assert-Contains $script 'component-config-whitelist' 'Allowlisted component configuration section is missing.'
Assert-Contains $script 'mysql hive kafka spark datax' 'The five requested components are not declared.'
Assert-Contains $script 'password\|passwd\|secret\|token\|credential' 'Sensitive-key filtering is missing.'
Assert-Contains $script 'inventory_only_not_component_verification' 'Evidence boundary is missing from summary.env.'
Assert-Contains $script 'data_write_permission' 'Key-directory status is missing from summary.env.'
Assert-Contains $script 'component\.hive\.stable_path_consistency' 'Hive stable-path drift summary is missing.'
Assert-Contains $script 'installed\.hive' 'Installed Hive-version inventory is missing.'
Assert-Contains $script 'java_process\.pid' 'Per-process Java executable evidence is missing.'
Assert-Contains $script 'java-8-openjdk-amd64' 'Java 8 runtime discovery is missing.'
Assert-Contains $script 'datax-current/bin/datax\.py' 'DataX current-link entry discovery is missing.'
Assert-Contains $script '\[\[ -r \$datax_candidate \]\]' 'Readable DataX Python-entry discovery is missing.'
Assert-Contains $script 'component\.datax\.python_version' 'DataX Python runtime evidence is missing.'
Assert-Contains $script 'stable\.datax_current' 'DataX current-link inventory is missing.'
Assert-Contains $script 'auto\.create\.topics\.enable' 'Kafka auto-create policy collection is missing.'
Assert-Contains $script 'delete\.topic\.enable' 'Kafka topic-delete policy collection is missing.'
Assert-Contains $script 'overall_status=PARTIAL' 'PARTIAL collection state is missing.'
Assert-Contains $script 'overall_status=COLLECTED' 'COLLECTED state is missing.'
Assert-Contains $script 'umask 077' 'Private output permission baseline is missing.'

$forbiddenPatterns = @(
    '(?im)^\s*(sudo\s+)?(apt|apt-get|yum|dnf)\s+install\b',
    '(?im)^\s*(sudo\s+)?(systemctl|service)\s+(start|stop|restart)\b',
    '(?im)^\s*(start|stop)-(dfs|yarn)\.sh\b',
    '(?im)hdfs\s+namenode\s+-format\b',
    '(?im)hdfs\s+dfs\s+-rm\b',
    '(?im)kafka-topics[^\r\n]*--create\b',
    '(?im)mysql[^\r\n]*\s-e\s+'
)
foreach ($pattern in $forbiddenPatterns) {
    Assert-NotContains $script $pattern "Forbidden mutating command matched: $pattern"
}

Assert-Contains $readme 'collect-vm-environment-evidence\.sh' 'README invocation is missing.'
Assert-Contains $readme 'COLLECTED' 'README does not explain COLLECTED.'
Assert-Contains $readme 'PARTIAL' 'README does not explain PARTIAL.'
Assert-Contains $readme 'verified' 'README does not preserve the component-verification boundary.'
Assert-Contains $readme '\.local-notes/m1-evidence/inbox/' 'README does not define the local evidence inbox.'
Assert-Contains $readme 'git check-ignore -v' 'README does not include the evidence ignore check.'

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output 'VM environment evidence collector contract: PASS'
exit 0
