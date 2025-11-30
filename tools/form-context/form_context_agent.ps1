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

# Устанавливаем кодировку для текущей сессии PowerShell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

#region Функции

function Import-EnvFile {
    <#
    .SYNOPSIS
        Загружает переменные окружения из .env файла
    #>
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
    Write-Host "ОШИБКА: $Message" -ForegroundColor Red
}

function Write-SuccessInfo {
    param([string]$Message)
    Write-Host "OK. $Message" -ForegroundColor Green
}

function New-TaskFile {
    <#
    .SYNOPSIS
        Создает управляющий файл task.json для агентского режима
    #>
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
    
    # Создаем директорию если нужно
    $taskDir = Split-Path $TaskFilePath -Parent
    if (-not (Test-Path $taskDir)) {
        New-Item -ItemType Directory -Path $taskDir -Force | Out-Null
    }
    
    # Записываем JSON
    $task | ConvertTo-Json -Depth 10 | Out-File -FilePath $TaskFilePath -Encoding UTF8
    
    Write-SuccessInfo "Создан файл задания: $TaskFilePath"
    return $TaskFilePath
}

function Wait-TaskCompletion {
    <#
    .SYNOPSIS
        Ожидает завершения обработки task.json
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$TaskFile,
        
        [Parameter(Mandatory=$true)]
        [int]$TimeoutSeconds
    )
    
    Write-Host "`nОжидание завершения (таймаут: ${TimeoutSeconds}с)..." -ForegroundColor Green
    
    $startTime = Get-Date
    $processingFile = "$TaskFile.processing"
    $completedFile = "$TaskFile.completed"
    $errorFile = "$TaskFile.error"
    
    # Ждем появления .processing
    Write-Host "   Ожидание начала обработки..." -NoNewline
    while (-not (Test-Path $processingFile) -and ((Get-Date) - $startTime).TotalSeconds -lt 120) {
        Start-Sleep -Milliseconds 500
        Write-Host "." -NoNewline
    }
    Write-Host ""
    
    if (-not (Test-Path $processingFile)) {
        Write-Host "ПРЕДУПРЕЖДЕНИЕ: файл .processing не появился" -ForegroundColor Yellow
        return "timeout"
    }
    
    Write-SuccessInfo "Обработка запущена"
    Write-Host "   Ожидание завершения..." -NoNewline
    
    # Ждем завершения
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

#region Загрузка .env и применение параметров

# Загружаем переменные окружения из .env файла (если существует)
$envLoaded = Import-EnvFile
if ($envLoaded) {
    Write-DebugInfo "Environment variables loaded from .env file"
}

# Приоритет: Параметр командной строки → .env файл → Значение по умолчанию
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

#region Валидация параметров

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Form Context Collector - Agent Mode" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

if (-not $InfoBasePath -and -not $InfoBaseName) {
    Write-ErrorInfo "Требуется InfoBasePath или InfoBaseName"
    Write-Host "   Используйте параметр -InfoBasePath или -InfoBaseName" -ForegroundColor Yellow
    exit 1
}

if (-not $Forms -and -not $FormsFile) {
    Write-ErrorInfo "Не указаны формы для обработки"
    Write-Host "   Используйте параметр -Forms или -FormsFile" -ForegroundColor Yellow
    exit 1
}

#endregion

#region Сбор списка форм

$formsList = @()

# Из параметра -Forms
if ($Forms) {
    foreach ($form in $Forms) {
        $formsList += @{
            type = "form_path"
            value = $form
        }
    }
}

# Из файла -FormsFile
if ($FormsFile) {
    if (-not (Test-Path $FormsFile)) {
        Write-ErrorInfo "Файл не найден: $FormsFile"
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
    Write-ErrorInfo "Список форм пуст"
    exit 1
}

Write-Host "Форм для обработки: $($formsList.Count)" -ForegroundColor Green
for ($i = 0; $i -lt $formsList.Count; $i++) {
    Write-Host "   $($i + 1). $($formsList[$i].value)"
}
Write-Host ""

#endregion

#region Подготовка task.json

$options = @{
    include_invisible = $IncludeInvisible.IsPresent
    generate_markdown = -not $NoMarkdown.IsPresent
    max_depth = 5
    close_after_collection = -not $NoClose.IsPresent
    wait_form_timeout = 2000
}

Write-Host "Настройки:" -ForegroundColor Green
Write-Host "   Включать невидимые: $($options.include_invisible)"
Write-Host "   Генерировать Markdown: $($options.generate_markdown)"
Write-Host "   Закрывать 1С: $($options.close_after_collection)"
Write-Host ""

# Определяем путь к task.json
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskFile = Join-Path $scriptDir "agent\task.json"

# Создаем task.json
$taskFile = New-TaskFile -FormsList $formsList -Options $options -TaskFilePath $taskFile

#endregion

#region Проверка 1cv8.exe и FormContextCollector.epf

# Проверка существования 1cv8.exe
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
    Write-ErrorInfo "1C:Enterprise platform (1cv8.exe) не найден"
    Write-Host ""
    Write-Host "Проверено: $V8Path" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Проверьте:" -ForegroundColor Cyan
    Write-Host "  1. 1C:Enterprise установлен" -ForegroundColor Gray
    Write-Host "  2. Правильный путь в V8_PATH (.env файл) или -V8Path" -ForegroundColor Gray
    Write-Host "  3. 1cv8.exe есть в system PATH" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-DebugInfo "Using 1C platform: $V8Path"

# Проверка обработки
$processingPath = Join-Path $scriptDir "FormContextCollector.epf"
if (-not (Test-Path $processingPath)) {
    Write-Host ""
    Write-ErrorInfo "Обработка не найдена: $processingPath"
    Write-Host "   Убедитесь, что FormContextCollector.epf находится в каталоге со скриптом" -ForegroundColor Yellow
    Write-Host "   Выполните: cd tools/form-context && build-epf.bat" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-DebugInfo "Processing file: $processingPath"

#endregion

#region Запуск 1С с обработкой

Write-Host "Запуск 1С..." -ForegroundColor Green

$arguments = @("ENTERPRISE")

# Параметры подключения к ИБ
if ($InfoBaseName) {
    $arguments += "/IBName", "`"$InfoBaseName`""
} else {
    $arguments += "/F", "`"$InfoBasePath`""
}

# Учетные данные
if ($UserName) { $arguments += "/N", "`"$UserName`"" }
if ($Password) { $arguments += "/P", "`"$Password`"" }

# Обработка для выполнения
$arguments += "/Execute", "`"$processingPath`""

# Отключение диалогов
$arguments += "/DisableStartupDialogs"

if ($DebugMode) {
    $cmdLine = "$V8Path $($arguments -join ' ')"
    Write-DebugInfo "Command: $cmdLine"
}

Write-Host "   База: $InfoBasePath$InfoBaseName"
Write-Host "   Обработка: $processingPath"
Write-Host ""

# Запуск 1С в фоне (неблокирующий)
try {
    $process = Start-Process -FilePath $V8Path `
                            -ArgumentList $arguments `
                            -PassThru
    
    Write-SuccessInfo "1С запущен (PID: $($process.Id))"
} catch {
    Write-ErrorInfo "Ошибка запуска 1С: $_"
    exit 1
}

#endregion

#region Ожидание завершения

if ($Wait) {
    $status = Wait-TaskCompletion -TaskFile $taskFile -TimeoutSeconds $Timeout
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    
    switch ($status) {
        "completed" {
            Write-SuccessInfo "Обработка завершена успешно"
            Write-Host "   Результаты сохранены в context/forms/" -ForegroundColor Gray
            exit 0
        }
        "error" {
            Write-ErrorInfo "Ошибка при обработке"
            Write-Host "   Проверьте лог: tools/form-context/debug.log" -ForegroundColor Yellow
            exit 1
        }
        "timeout" {
            Write-Host "ПРЕДУПРЕЖДЕНИЕ: Превышен таймаут ожидания" -ForegroundColor Yellow
            Write-Host "   Обработка может продолжать работу в фоне" -ForegroundColor Gray
            exit 2
        }
    }
} else {
    Write-SuccessInfo "1С запущен в фоновом режиме"
    Write-Host "   Проверьте статус: task.json.processing → task.json.completed" -ForegroundColor Gray
    Write-Host ""
    exit 0
}

#endregion