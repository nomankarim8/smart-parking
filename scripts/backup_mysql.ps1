param(
    [string]$EnvPath = (Join-Path $PSScriptRoot '..\backend\.env'),
    [string]$BackupDirectory = (Join-Path $PSScriptRoot '..\backups'),
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'mysql-tools.ps1')
$db = Get-SmartParkingDbConfig -EnvPath (Resolve-Path -LiteralPath $EnvPath)
$tools = Get-SmartParkingMySqlTools
$credential = New-SmartParkingMySqlOptionFile -DbConfig $db

try {
    & $tools.Client "--defaults-extra-file=$($credential.Path)" --batch --skip-column-names --execute 'SELECT 1' | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "MySQL connection check failed with exit code $LASTEXITCODE"
    }
    if ($CheckOnly) {
        Write-Output "MySQL connection verified for database '$($db['DB_NAME'])' on port $($db['DB_PORT'])."
    } else {
        $resolvedBackupDirectory = [IO.Path]::GetFullPath($BackupDirectory)
        foreach ($publicPath in @(
            (Join-Path $PSScriptRoot '..\frontend\public'),
            (Join-Path $PSScriptRoot '..\backend\uploads')
        )) {
            $resolvedPublicPath = [IO.Path]::GetFullPath($publicPath).TrimEnd('\') + '\'
            if ($resolvedBackupDirectory.StartsWith($resolvedPublicPath, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Backup location must be outside public/static and uploads directories.'
            }
        }

        $backupDirectoryExisted = Test-Path -LiteralPath $resolvedBackupDirectory -PathType Container
        New-Item -ItemType Directory -Path $resolvedBackupDirectory -Force | Out-Null
        if (-not $backupDirectoryExisted) {
            Protect-SmartParkingBackupDirectory -Path $resolvedBackupDirectory
        }
        $timestamp = [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss')
        $backupPath = Join-Path $resolvedBackupDirectory "$($db['DB_NAME'])_$timestamp.sql"
        & $tools.Dump "--defaults-extra-file=$($credential.Path)" --single-transaction --routines --triggers --events --databases $db['DB_NAME'] "--result-file=$backupPath"
        if ($LASTEXITCODE -ne 0) {
            if (Test-Path -LiteralPath $backupPath) {
                Remove-Item -LiteralPath $backupPath -Force
            }
            throw "mysqldump failed with exit code $LASTEXITCODE"
        }
        if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf) -or (Get-Item -LiteralPath $backupPath).Length -lt 100) {
            throw 'mysqldump returned success but the backup file is missing or unexpectedly small.'
        }

        Write-Output "Backup created: $backupPath"
        Write-Output "Size: $((Get-Item -LiteralPath $backupPath).Length) bytes"
    }
} finally {
    Remove-Item -LiteralPath $credential.Directory -Recurse -Force -ErrorAction SilentlyContinue
}
