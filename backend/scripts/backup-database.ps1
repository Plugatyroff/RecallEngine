<#
.SYNOPSIS
    Back up the Recall Engine database to a folder, keeping the most recent copies.

.DESCRIPTION
    1. Asks SQL Server to write a full backup into its own backup folder
       (SQL Server runs under its own Windows account and can always write there).
    2. Checks that the backup file is readable and undamaged.
    3. Copies it into the destination folder with the date in its name.
    4. Deletes the oldest copies so that only the last -Keep backups remain.

    Runs at most once per day unless -Force is given, so it is safe to run at every login.
    The server and database names are read from backend/.env.

.EXAMPLE
    .\backup-database.ps1
    .\backup-database.ps1 -Destination D:\Backups -Keep 30 -Force
#>
param(
    [string]$Destination = (Join-Path $env:USERPROFILE "RecallEngine-backups"),
    [int]$Keep = 14,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Read DB_SERVER and DB_NAME from backend/.env (KEY=value lines).
$envFile = Join-Path $PSScriptRoot "..\.env"
$settings = @{}
Get-Content $envFile | Where-Object { $_ -match "^\s*([A-Z_]+)\s*=\s*(.*)$" } | ForEach-Object {
    $settings[$Matches[1]] = $Matches[2].Trim()
}
$server = $settings["DB_SERVER"]
$database = $settings["DB_NAME"]
if (-not $server -or -not $database) { throw "DB_SERVER and DB_NAME must be set in $envFile" }

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$log = Join-Path $Destination "backup.log"
function Write-Log([string]$message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $message"
    Write-Host $line
    Add-Content -Path $log -Value $line
}

function Invoke-Sql([string]$query) {
    # -E: Windows login, -C: trust the local self-signed certificate, -b: fail on SQL errors
    $output = sqlcmd -S $server -E -C -b -W -h -1 -Q "SET NOCOUNT ON; $query" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "SQL Server error: $output" }
    return $output
}

try {
    $today = Get-Date -Format "yyyy-MM-dd"
    if (-not $Force -and (Get-ChildItem $Destination -Filter "${database}_$today*.bak")) {
        Write-Host "A backup from today already exists in $Destination. Use -Force to make another."
        exit 0
    }

    $serverFolder = (Invoke-Sql "SELECT CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(400));" | Select-Object -First 1).Trim()
    # A fixed name, overwritten each time (WITH INIT), so files never pile up in SQL Server's folder.
    $serverFile = Join-Path $serverFolder "${database}_latest.bak"

    Invoke-Sql "BACKUP DATABASE [$database] TO DISK = N'$serverFile' WITH INIT, CHECKSUM;" | Out-Null
    Invoke-Sql "RESTORE VERIFYONLY FROM DISK = N'$serverFile' WITH CHECKSUM;" | Out-Null

    $target = Join-Path $Destination "${database}_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').bak"
    Copy-Item -LiteralPath $serverFile -Destination $target
    Write-Log "OK      $target ($([math]::Round((Get-Item $target).Length / 1MB, 1)) MB)"

    Get-ChildItem $Destination -Filter "${database}_*.bak" |
        Sort-Object Name -Descending |
        Select-Object -Skip $Keep |
        ForEach-Object {
            Remove-Item -LiteralPath $_.FullName
            Write-Log "DELETED $($_.Name) (keeping the newest $Keep)"
        }
}
catch {
    Write-Log "FAILED  $($_.Exception.Message)"
    exit 1
}
