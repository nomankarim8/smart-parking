param(
    [string]$EnvPath = (Join-Path $PSScriptRoot '..\backend\.env'),
    [string]$BackupDirectory = (Join-Path $PSScriptRoot '..\backups'),
    [string]$RestoreDatabase = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'mysql-tools.ps1')
$resolvedEnv = (Resolve-Path -LiteralPath $EnvPath -ErrorAction Stop).Path
$db = Get-SmartParkingDbConfig -EnvPath $resolvedEnv
if ([string]::IsNullOrWhiteSpace($RestoreDatabase)) {
    $RestoreDatabase = 'smart_parking_restore_test_' + [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
}
if ($RestoreDatabase -notmatch '^smart_parking_restore_test_[0-9]{14}$') {
    throw 'Restore target must match smart_parking_restore_test_YYYYMMDDHHMMSS exactly.'
}
if ($RestoreDatabase -eq $db['DB_NAME']) {
    throw 'Restore target must not be the configured source database.'
}

$tools = Get-SmartParkingMySqlTools
$credential = New-SmartParkingMySqlOptionFile -DbConfig $db
$created = $false
$tempSql = Join-Path $env:TEMP ($RestoreDatabase + '.sql')
try {
    $existingTarget = (& $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='$RestoreDatabase'" | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify the isolated restore database name.' }
    if ($existingTarget -ne '0') { throw "Restore database '$RestoreDatabase' already exists; refusing to reuse or remove it." }

    $backupOutput = @(& (Join-Path $PSScriptRoot 'backup_mysql.ps1') -EnvPath $resolvedEnv -BackupDirectory $BackupDirectory)
    if ($LASTEXITCODE -ne 0) { throw 'Source database backup failed.' }
    $backupLine = $backupOutput | Where-Object { $_ -like 'Backup created: *' } | Select-Object -First 1
    if (-not $backupLine) { throw 'Backup script did not report a backup file.' }
    $backupPath = $backupLine.Substring('Backup created: '.Length)
    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) { throw 'Backup file does not exist.' }
    $backupInfo = Get-Item -LiteralPath $backupPath
    if ($backupInfo.Length -lt 100) { throw 'Backup file is unexpectedly small.' }
    $backupHash = (Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash
    $sql = [IO.File]::ReadAllText($backupPath)
    $sourceDb = [regex]::Escape($db['DB_NAME'])
    if ($sql -notmatch ('CREATE DATABASE.*`' + $sourceDb + '`') -or $sql -notmatch ('(?m)^USE `' + $sourceDb + '`;')) {
        throw 'Backup does not contain expected database selection statements.'
    }
    $sql = [regex]::Replace(
        $sql,
        ('(?m)^(CREATE DATABASE.*`)' + $sourceDb + '(`.*)$'),
        ('$1' + $RestoreDatabase + '$2')
    )
    $sql = [regex]::Replace($sql, ('(?m)^USE `' + $sourceDb + '`;'), ('USE `' + $RestoreDatabase + '`;'))
    [IO.File]::WriteAllText($tempSql, $sql, (New-Object System.Text.UTF8Encoding($false)))

    $dbName = '`' + $RestoreDatabase + '`'
    & $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute "CREATE DATABASE $dbName CHARACTER SET utf8mb4"
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the isolated restore database.' }
    $created = $true

    $restoreCommand = '"{0}" --defaults-extra-file="{1}" < "{2}"' -f $tools.Client, $credential.Path, $tempSql
    & $env:ComSpec /d /c $restoreCommand
    if ($LASTEXITCODE -ne 0) { throw "Restore failed with exit code $LASTEXITCODE." }

    $tableQuery = "SELECT table_name FROM information_schema.tables WHERE table_schema='$RestoreDatabase' AND table_type='BASE TABLE' ORDER BY table_name"
    $tables = @(& $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute $tableQuery)
    if ($LASTEXITCODE -ne 0 -or $tables.Count -eq 0) { throw 'Restored schema contains no tables.' }
    $sourceTableQuery = "SELECT table_name FROM information_schema.tables WHERE table_schema='$($db['DB_NAME'])' AND table_type='BASE TABLE' ORDER BY table_name"
    $sourceTables = @(& $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute $sourceTableQuery)
    if ($LASTEXITCODE -ne 0 -or ($tables -join "`n") -ne ($sourceTables -join "`n")) {
        throw 'Restored table list differs from the source database.'
    }

    $comparisons = @()
    foreach ($table in $tables) {
        if ($table -notmatch '^[A-Za-z0-9_]+$') { throw 'Unexpected table identifier returned by MySQL.' }
        $countQuery = "SELECT (SELECT COUNT(*) FROM ``$($db['DB_NAME'])``.``$table``), (SELECT COUNT(*) FROM $dbName.``$table``)"
        $countResult = (& $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute $countQuery | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $countResult -notmatch '^([0-9]+)\s+([0-9]+)$' -or $Matches[1] -ne $Matches[2]) {
            throw "Row-count mismatch for table '$table': $countResult"
        }
        $comparisons += [pscustomobject]@{ Table = $table; Rows = [long]$Matches[1] }
    }

    $integrityQuery = "SELECT (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema='$($db['DB_NAME'])' AND index_name='PRIMARY'), (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema='$RestoreDatabase' AND index_name='PRIMARY'), (SELECT COUNT(*) FROM information_schema.key_column_usage WHERE table_schema='$($db['DB_NAME'])' AND referenced_table_name IS NOT NULL), (SELECT COUNT(*) FROM information_schema.key_column_usage WHERE table_schema='$RestoreDatabase' AND referenced_table_name IS NOT NULL)"
    $integrity = (& $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute $integrityQuery | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $integrity -notmatch '^([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)$' -or $Matches[1] -ne $Matches[2] -or $Matches[3] -ne $Matches[4]) {
        throw "Primary-key or foreign-key metadata differs: $integrity"
    }

    $joinQuery = "SELECT COUNT(*) FROM $dbName.parking_records pr JOIN $dbName.vehicles v ON v.vehicle_id=pr.vehicle_id JOIN $dbName.parking_slots s ON s.slot_id=pr.slot_id"
    & $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute $joinQuery | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Representative application join query failed against the restored database.' }

    Write-Output "Restore verification PASS"
    Write-Output "Backup: $backupPath"
    Write-Output "Backup SHA256: $backupHash"
    Write-Output "Restore database: $RestoreDatabase"
    Write-Output "Tables verified: $($tables.Count)"
    Write-Output "Primary-key / foreign-key metadata: $integrity"
    $comparisons | Where-Object { $_.Table -in @('users','vehicles','parking_records','payments','parking_slots') } | Format-Table -AutoSize | Out-String | Write-Output
} finally {
    if ($created -and $RestoreDatabase -match '^smart_parking_restore_test_[0-9]{14}$' -and $RestoreDatabase -ne $db['DB_NAME']) {
        & $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute "DROP DATABASE IF EXISTS ``$RestoreDatabase``" | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Error "Could not remove the verified disposable database '$RestoreDatabase'." }
    }
    Remove-Item -LiteralPath $tempSql -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $credential.Directory -Recurse -Force -ErrorAction SilentlyContinue
}
