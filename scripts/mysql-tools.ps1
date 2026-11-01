function Get-SmartParkingDbConfig {
    param([Parameter(Mandatory = $true)][string]$EnvPath)

    if (-not (Test-Path -LiteralPath $EnvPath -PathType Leaf)) {
        throw "Database environment file not found: $EnvPath"
    }

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $EnvPath) {
        if ($line -match '^\s*(DB_HOST|DB_PORT|DB_USER|DB_PASSWORD|DB_NAME)\s*=\s*(.*)\s*$') {
            $values[$Matches[1]] = $Matches[2]
        }
    }
    foreach ($key in @('DB_HOST', 'DB_PORT', 'DB_USER', 'DB_NAME')) {
        if (-not $values.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($values[$key])) {
            throw "Required database setting $key is missing from $EnvPath"
        }
    }
    if (-not $values.ContainsKey('DB_PASSWORD')) {
        $values['DB_PASSWORD'] = ''
    }
    return $values
}

function Get-SmartParkingMySqlTools {
    $directory = 'C:\xampp\mysql\bin'
    $client = Join-Path $directory 'mysql.exe'
    $dump = Join-Path $directory 'mysqldump.exe'
    if (-not (Test-Path -LiteralPath $client -PathType Leaf)) {
        $client = (Get-Command mysql.exe -ErrorAction Stop).Source
    }
    if (-not (Test-Path -LiteralPath $dump -PathType Leaf)) {
        $dump = (Get-Command mysqldump.exe -ErrorAction Stop).Source
    }
    return @{ Client = $client; Dump = $dump }
}

function Protect-SmartParkingBackupDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetOwner($identity)
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object Security.AccessControl.FileSystemAccessRule(
        $identity,
        [Security.AccessControl.FileSystemRights]::FullControl,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function New-SmartParkingMySqlOptionFile {
    param([Parameter(Mandatory = $true)][hashtable]$DbConfig)

    $directory = Join-Path $env:TEMP ("smart-parking-mysql-" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $directory -ErrorAction Stop | Out-Null
    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
        $acl = New-Object Security.AccessControl.DirectorySecurity
        $acl.SetOwner($identity)
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object Security.AccessControl.FileSystemAccessRule(
            $identity,
            [Security.AccessControl.FileSystemRights]::FullControl,
            [Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($rule)
        Set-Acl -LiteralPath $directory -AclObject $acl

        $escape = {
            param([string]$Value)
            return $Value.Replace('\', '\\').Replace('"', '\"')
        }

        $lines = @(
            '[client]',
            ('host="' + (& $escape $DbConfig['DB_HOST']) + '"'),
            ('port=' + $DbConfig['DB_PORT']),
            ('user="' + (& $escape $DbConfig['DB_USER']) + '"')
        )
        if (-not [string]::IsNullOrEmpty($DbConfig['DB_PASSWORD'])) {
            $lines += 'password="' + (& $escape $DbConfig['DB_PASSWORD']) + '"'
        }
        $lines += @('', '[mysql]', ('database="' + (& $escape $DbConfig['DB_NAME']) + '"'))
        $optionFile = Join-Path $directory 'client.cnf'
        [IO.File]::WriteAllLines($optionFile, $lines, [Text.Encoding]::ASCII)
        return @{ Path = $optionFile; Directory = $directory }
    } catch {
        Remove-Item -LiteralPath $directory -Recurse -Force -ErrorAction SilentlyContinue
        throw
    }
}
