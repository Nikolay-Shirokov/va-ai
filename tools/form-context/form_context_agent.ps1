<#
.SYNOPSIS
    Form Context Collector - Agent Mode CLI (PowerShell)

.DESCRIPTION
    Автоматический сбор контекста форм 1С для AI-ассистентов.
    Создает task.json, запускает 1С с обработкой и ожидает завершения.

.PARAMETER InfoBasePath
    Путь к файловой базе (File=C:/Bases/Test/)

.PARAMETER InfoBaseName
    Имя базы из списка информационных баз

.PARAMETER UserName
    Имя пользователя 1С

.PARAMETER Password
    Пароль пользователя

.PARAMETER Forms
    Массив форм для обработки

.PARAMETER FormsFile
    Файл со списком форм (по одной на строку)

.PARAMETER V8Path
    Путь к 1cv8.exe (по умолчанию из PATH или .env)

.PARAMETER IncludeInvisible
    Включать невидимые элементы

.PARAMETER NoMarkdown
    Не генерировать Markdown

.PARAMETER NoClose
    Не закрывать 1С после завершения

.PARAMETER Wait
    Ждать завершения обработки

.PARAMETER Timeout
    Таймаут ожидания в секундах (по умолчанию 300)

.PARAMETER DebugMode
    Режим отладки с дополнительным выводом

.EXAMPLE
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказПокупателя")

.EXAMPLE
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -FormsFile "forms.txt" -Wait

.EXAMPLE
    .\form_context_agent.ps1 -InfoBaseName "MyBase" -Forms @("Справочник.Контрагенты") -NoClose

.NOTES
    Требует: 1cv8.exe, FormContextCollector.epf
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$InfoBasePath,
    
    [Parameter(Mandatory=$false)]
    [string]$InfoBaseName,
    
    [Parameter(Mandatory=$false)]
    [string]$UserName,
    
    [Parameter(Mandatory=$false)]
    [string]$Password,
    
    [Parameter(Mandatory=$false)]
    [string[]]$Forms,
    
    [Parameter(Mandatory=$false)]
    [string]$FormsFile,
    
    [Parameter(Mandatory=$false)]
    [string]$V8Path = "1cv8.exe",
    
    [Parameter(Mandatory=$false)]
    [switch]$IncludeInvisible,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoMarkdown,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoClose,
    
    [Parameter(Mandatory=$false)]
    [switch]$Wait,
    
    [Parameter(Mandatory=$false)]
    [int]$Timeout = 300,
    
    [Parameter(Mandatory=$false)]
    [switch]$DebugMode
)

# Set encoding
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

#region Functions

function Import-EnvFile {
    param([string]$EnvFilePath = ".env")
    
    if (Test-Path $EnvFilePath) {
        Get-Content $EnvFilePath -Encoding UTF8 | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith('#')) {
                if ($line -match '^([^=]+)=(.*)$') {
                    $name = $matches[1].Trim()
                    $value = $matches[2].Trim()
                    $value = $value -replace '^["'']|["'']$', ''
                    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
                }
            }
        }
        return $true
    }
    return $false
}

function Write-DebugInfo {
    param([string]$Message)
    if ($DebugMode) {
        Write-Host "[DEBUG] $Message" -ForegroundColor Cyan
    }
}

function Write-ErrorInfo {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
}

function Write-SuccessInfo {
    param([string]$Message)
    Write-Host "OK. $Message" -ForegroundColor Green
}

function New-TaskFile {
    param(
        [Parameter(Mandatory=$true)]
        [array]$FormsList,
        
        [Parameter(Mandatory=$true)]
        [hashtable]$Options,
        
        [Parameter(Mandatory=$true)]
        [string]$TaskFilePath
    )
    
    $task = @{
        version = "1.0"
        mode = "agent"
        forms = $FormsList
        options = $Options
    }
    
    $taskDir = Split-Path $TaskFilePath -Parent
    if (-not (Test-Path $taskDir)) {
        New-Item -ItemType Directory -Path $taskDir -Force | Out-Null
    }
    
    $task | ConvertTo-Json -Depth 10 | Out-File -FilePath $TaskFilePath -Encoding UTF8
    
    Write-SuccessInfo "Task file created: $TaskFilePath"
    return $TaskFilePath
}

function Wait-TaskCompletion {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TaskFile,
        
        [Parameter(Mandatory=$true)]
        [int]$TimeoutSeconds
    )
    
    Write-Host "`nWaiting for completion (timeout: ${TimeoutSeconds}s)..." -ForegroundColor Green
    
    $startTime = Get-Date
    $processingFile = "$TaskFile.processing"
    $completedFile = "$TaskFile.completed"
    $errorFile = "$TaskFile.error"
    
    Write-Host "   Waiting for processing to start..." -NoNewline
    while (-not (Test-Path $processingFile) -and ((Get-Date) - $startTime).TotalSeconds -lt 120) {
        Start-Sleep -Milliseconds 500
        Write-Host "." -NoNewline
    }
    Write-Host ""
    
    if (-not (Test-Path $processingFile)) {
        Write-Host "WARNING: processing file did not appear" -ForegroundColor Yellow
        return "timeout"
    }
    
    Write-SuccessInfo "Processing started"
    Write-Host "   Waiting for completion..." -NoNewline
    
    while (((Get-Date) - $startTime).TotalSeconds -lt $TimeoutSeconds) {
        if (Test-Path $completedFile) {
            Write-Host ""
            return "completed"
        }
        elseif (Test-Path $errorFile) {
            Write-Host ""
            return "error"
        }
        
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
    }
    
    Write-Host ""
    return "timeout"
}

#endregion

#region Load .env and apply parameters

$envLoaded = Import-EnvFile
if ($envLoaded) {
    Write-DebugInfo "Environment variables loaded from .env file"
}

if (-not $PSBoundParameters.ContainsKey('V8Path')) {
    $envV8Path = [Environment]::GetEnvironmentVariable('V8_PATH', 'Process')
    if ($envV8Path) { $V8Path = $envV8Path }
}

if (-not $PSBoundParameters.ContainsKey('InfoBasePath')) {
    $envInfoBasePath = [Environment]::GetEnvironmentVariable('INFOBASE_PATH', 'Process')
    if ($envInfoBasePath) { $InfoBasePath = $envInfoBasePath }
}

if (-not $PSBoundParameters.ContainsKey('InfoBaseName')) {
    $envInfoBaseName = [Environment]::GetEnvironmentVariable('INFOBASE_NAME', 'Process')
    if ($envInfoBaseName) { $InfoBaseName = $envInfoBaseName }
}

if (-not $PSBoundParameters.ContainsKey('UserName')) {
    $envUserName = [Environment]::GetEnvironmentVariable('USERNAME_1C', 'Process')
    if ($envUserName) { $UserName = $envUserName }
}

if (-not $PSBoundParameters.ContainsKey('Password')) {
    $envPassword = [Environment]::GetEnvironmentVariable('PASSWORD_1C', 'Process')
    if ($envPassword) { $Password = $envPassword }
}

#endregion

#region Validate parameters

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Form Context Collector - Agent Mode" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

if (-not $InfoBasePath -and -not $InfoBaseName) {
    Write-ErrorInfo "InfoBasePath or InfoBaseName required"
    Write-Host "   Use -InfoBasePath or -InfoBaseName parameter" -ForegroundColor Yellow
    exit 1
}

if (-not $Forms -and -not $FormsFile) {
    Write-ErrorInfo "No forms specified for processing"
    Write-Host "   Use -Forms or -FormsFile parameter" -ForegroundColor Yellow
    exit 1
}

#endregion

#region Collect forms list

$formsList = @()

if ($Forms) {
    foreach ($form in $Forms) {
        $formsList += @{
            type = "form_path"
            value = $form
        }
    }
}

if ($FormsFile) {
    if (-not (Test-Path $FormsFile)) {
        Write-ErrorInfo "File not found: $FormsFile"
        exit 1
    }
    
    Get-Content $FormsFile -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            $formsList += @{
                type = "form_path"
                value = $line
            }
        }
    }
}

if ($formsList.Count -eq 0) {
    Write-ErrorInfo "Forms list is empty"
    exit 1
}

Write-Host "Forms to process: $($formsList.Count)" -ForegroundColor Green
for ($i = 0; $i -lt $formsList.Count; $i++) {
    Write-Host "   $($i + 1). $($formsList[$i].value)"
}
Write-Host ""

#endregion

#region Prepare task.json

$options = @{
    include_invisible = $IncludeInvisible.IsPresent
    generate_markdown = -not $NoMarkdown.IsPresent
    max_depth = 5
    close_after_collection = -not $NoClose.IsPresent
    wait_form_timeout = 2000
}

Write-Host "Settings:" -ForegroundColor Green
Write-Host "   Include invisible: $($options.include_invisible)"
Write-Host "   Generate Markdown: $($options.generate_markdown)"
Write-Host "   Close 1C: $($options.close_after_collection)"
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskFile = Join-Path $scriptDir "agent\task.json"

$taskFile = New-TaskFile -FormsList $formsList -Options $options -TaskFilePath $taskFile

# Добавляем паузу, чтобы файл task.json успел создаться на диске перед запуском 1С
Start-Sleep -Seconds 1

#endregion

#region Check 1cv8.exe and FormContextCollector.epf

$v8Exists = $false
if ([System.IO.Path]::IsPathRooted($V8Path)) {
    $v8Exists = Test-Path $V8Path
} else {
    try {
        $null = Get-Command $V8Path -ErrorAction Stop
        $v8Exists = $true
    } catch {
        $v8Exists = $false
    }
}

if (-not $v8Exists) {
    Write-Host ""
    Write-ErrorInfo "1C:Enterprise platform (1cv8.exe) not found"
    Write-Host ""
    Write-Host "Checked: $V8Path" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please verify:" -ForegroundColor Cyan
    Write-Host "  1. 1C:Enterprise is installed" -ForegroundColor Gray
    Write-Host "  2. Correct path in V8_PATH (.env file) or -V8Path" -ForegroundColor Gray
    Write-Host "  3. 1cv8.exe is in system PATH" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-DebugInfo "Using 1C platform: $V8Path"

$processingPath = Join-Path $scriptDir "FormContextCollector.epf"
if (-not (Test-Path $processingPath)) {
    Write-Host ""
    Write-ErrorInfo "Processing not found: $processingPath"
    Write-Host "   Make sure FormContextCollector.epf is in the script directory" -ForegroundColor Yellow
    Write-Host "   Run: cd tools/form-context && build-epf.bat" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-DebugInfo "Processing file: $processingPath"

#endregion

#region Launch 1C with processing

Write-Host "Launching 1C..." -ForegroundColor Green

$arguments = @("ENTERPRISE")

if ($InfoBaseName) {
    $arguments += "/IBName", "`"$InfoBaseName`""
} else {
    $arguments += "/F", "`"$InfoBasePath`""
}

if ($UserName) { $arguments += "/N", "`"$UserName`"" }
if ($Password) { $arguments += "/P", "`"$Password`"" }

$arguments += "/Execute", "`"$processingPath`""
$arguments += "/DisableStartupDialogs"

if ($DebugMode) {
    $cmdLine = "$V8Path $($arguments -join ' ')"
    Write-DebugInfo "Command: $cmdLine"
}

Write-Host "   Database: $InfoBasePath$InfoBaseName"
Write-Host "   Processing: $processingPath"
Write-Host ""

try {
    $process = Start-Process -FilePath $V8Path `
                            -ArgumentList $arguments `
                            -PassThru
    
    Write-SuccessInfo "1C launched (PID: $($process.Id))"
} catch {
    Write-ErrorInfo "Failed to launch 1C: $_"
    exit 1
}

#endregion

#region Wait for completion

if ($Wait) {
    $status = Wait-TaskCompletion -TaskFile $taskFile -TimeoutSeconds $Timeout
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    
    switch ($status) {
        "completed" {
            Write-SuccessInfo "Processing completed successfully"
            Write-Host "   Results saved in context/forms/" -ForegroundColor Gray
            exit 0
        }
        "error" {
            Write-ErrorInfo "Error during processing"
            Write-Host "   Check log: tools/form-context/debug.log" -ForegroundColor Yellow
            exit 1
        }
        "timeout" {
            Write-Host "WARNING: Timeout exceeded" -ForegroundColor Yellow
            Write-Host "   Processing may continue in background" -ForegroundColor Gray
            exit 2
        }
    }
} else {
    Write-SuccessInfo "1C launched in background mode"
    Write-Host "   Check status: task.json.processing -> task.json.completed" -ForegroundColor Gray
    Write-Host ""
    exit 0
}

#endregion