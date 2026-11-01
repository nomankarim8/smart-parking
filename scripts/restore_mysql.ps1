param(
    [Parameter(Mandatory = $true)][string]$BackupFile,
    [string]$EnvPath = (Join-Path $PSScriptRoot '..\backend\.env')
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'mysql-tools.ps1')
$restorePath = (Resolve-Path -LiteralPath $BackupFile -ErrorAction Stop).Path
if ([IO.Path]::GetExtension($restorePath) -ne '.sql') {
    throw 'Restore input must be a trusted .sql file created for this application.'
}
$db = Get-SmartParkingDbConfig -EnvPath (Resolve-Path -LiteralPath $EnvPath)
$targetDb = $db['DB_NAME']
$databaseDeclaration = Select-String -LiteralPath $restorePath -Pattern ('CREATE DATABASE.*`' + [regex]::Escape($targetDb) + '`') -Quiet
if (-not $databaseDeclaration) {
    throw "The selected SQL file does not declare the configured database '$targetDb'."
}

$confirmation = Read-Host "This restore can replace tables in '$targetDb'. Type RESTORE $targetDb to continue"
if ($confirmation -cne "RESTORE $targetDb") {
    throw 'Restore cancelled; no database changes were made.'
}

$backupScript = Join-Path $PSScriptRoot 'backup_mysql.ps1'
$safetyOutput = @(& $backupScript -EnvPath $EnvPath)
if ($LASTEXITCODE -ne 0) {
    throw 'Pre-restore safety backup failed; restore was not started.'
}
$safetyLine = $safetyOutput | Where-Object { $_ -like 'Backup created: *' } | Select-Object -First 1
if (-not $safetyLine) {
    throw 'Pre-restore backup did not report a backup file; restore was not started.'
}
Write-Output $safetyLine

$tools = Get-SmartParkingMySqlTools
$credential = New-SmartParkingMySqlOptionFile -DbConfig $db
try {
    $command = '"{0}" --defaults-extra-file="{1}" < "{2}"' -f $tools.Client, $credential.Path, $restorePath
    & $env:ComSpec /d /c $command
    if ($LASTEXITCODE -ne 0) {
        throw "MySQL restore failed with exit code $LASTEXITCODE. The pre-restore safety backup is retained."
    }
    Write-Output "Restore completed for '$targetDb'. Verify the application before removing the safety backup."
} finally {
    Remove-Item -LiteralPath $credential.Directory -Recurse -Force -ErrorAction SilentlyContinue
}
