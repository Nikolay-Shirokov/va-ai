<#
.SYNOPSIS
    Form Context Collector - Agent Mode CLI (PowerShell)
    
    Автоматический сбор контекста форм 1С для AI-ассистентов и тестирования.

.DESCRIPTION
    Скрипт для автоматизации сбора структурного контекста форм 1С:Enterprise.
    
    Основные возможности:
    - Автоматический запуск 1С с обработкой сбора контекста
    - Поддержка файловых и клиент-серверных баз
    - Пакетная обработка списка форм из файла
    - Асинхронный режим с отслеживанием статуса
    - Настройка параметров сбора через командную строку
    - Интеграция с .env файлом для хранения учетных данных
    
    Рабочий процесс:
    1. Скрипт создает файл задания agent\task.json с параметрами
    2. Запускает 1С с обработкой FormContextCollector.epf
    3. Обработка читает task.json и выполняет сбор контекста
    4. Результаты сохраняются в context\forms\ (JSON + Markdown)
    5. Статус записывается в task.json.completed/error
    
    Результаты работы:
    - context\forms\index.json - индекс обработанных форм
    - context\forms\*.json - структура каждой формы
    - context\forms\*.md - человекочитаемое описание (опционально)

.PARAMETER InfoBasePath
    Путь к файловой информационной базе 1С.
    
    Формат: C:\Bases\MyBase\ или C:\Bases\MyBase
    Альтернатива: Используйте -InfoBaseName для зарегистрированных баз
    Из .env: INFOBASE_PATH
    
    Обязательный: Да (если не указан -InfoBaseName)

.PARAMETER InfoBaseName
    Имя информационной базы из списка 1С (для клиент-серверных или зарегистрированных баз).
    
    Используется для баз, зарегистрированных в списке информационных баз 1С.
    Альтернатива: Используйте -InfoBasePath для прямого указания пути
    Из .env: INFOBASE_NAME
    
    Обязательный: Да (если не указан -InfoBasePath)

.PARAMETER UserName
    Имя пользователя для подключения к информационной базе 1С.
    
    Опциональный параметр, если база не требует авторизации.
    Из .env: USERNAME_1C

.PARAMETER Password
    Пароль пользователя для подключения к информационной базе.
    
    Рекомендуется использовать .env файл вместо передачи в командной строке.
    Из .env: PASSWORD_1C

.PARAMETER Forms
    Массив полных путей к формам для обработки.
    
    Формат: "Тип.ИмяОбъекта.Форма.ИмяФормы"
    Примеры типов: Документ, Справочник, Обработка, Отчет
    
    Обязательный: Да (если не указан -FormsFile)
    
    Пример одной формы:
        @("Документ.ЗаказКлиента.Форма.ФормаДокумента")
    
    Пример нескольких форм:
        @("Документ.ЗаказКлиента.Форма.ФормаДокумента",
          "Справочник.Контрагенты.Форма.ФормаЭлемента")

.PARAMETER FormsFile
    Путь к текстовому файлу со списком форм (одна форма на строку).
    
    Формат файла:
    - Кодировка UTF-8
    - Одна форма на строку
    - Пустые строки игнорируются
    - Строки начинающиеся с # считаются комментариями
    
    Обязательный: Да (если не указан -Forms)
    
    Пример файла forms.txt:
        # Документы
        Документ.ЗаказКлиента.Форма.ФормаДокумента
        Документ.РеализацияТоваров.Форма.ФормаДокумента
        
        # Справочники
        Справочник.Контрагенты.Форма.ФормаЭлемента

.PARAMETER V8Path
    Путь к исполняемому файлу платформы 1С (1cv8.exe).
    
    По умолчанию: 1cv8.exe (ищется в PATH)
    Из .env: V8_PATH
    
    Примеры:
        "1cv8.exe" - из PATH
        "C:\Program Files\1cv8\8.3.24.1634\bin\1cv8.exe" - полный путь

.PARAMETER IncludeInvisible
    Включать невидимые элементы формы в результаты сбора контекста.
    
    По умолчанию невидимые элементы (с Видимость=Ложь) исключаются.
    Используйте этот флаг для полного анализа структуры формы.
    
    Передается в обработку как: options.include_invisible = true
    Влияет на: Объект.ВключатьНевидимыеЭлементы

.PARAMETER NoMarkdown
    Отключить генерацию Markdown-файлов с описанием форм.
    
    По умолчанию создаются только MD файлы (для людей).
    Используйте этот флаг, если нужны только JSON-файлы.
    
    Передается в обработку как: options.generate_markdown = false
    Влияет на: Объект.ГенерироватьMarkdown

.PARAMETER NoJson
    Отключить генерацию JSON-файлов с данными форм.
    
    По умолчанию создаются только MD файлы (для людей).
    Если нужны JSON-файлы для программной обработки, НЕ используйте этот флаг.
    
    Передается в обработку как: options.generate_json = false
    Влияет на: Объект.ГенерироватьJSON

.PARAMETER NoClose
    Не закрывать 1С автоматически после завершения обработки.
    
    По умолчанию 1С закрывается после обработки всех форм.
    Полезно для отладки или визуального просмотра результатов.
    
    Передается в обработку как: options.close_after_collection = false

.PARAMETER Wait
    Ждать завершения обработки перед выходом из скрипта.
    
    По умолчанию скрипт запускает 1С и сразу завершается.
    С этим флагом скрипт ожидает появления файла task.json.completed/error.
    
    Полезно для:
    - CI/CD пайплайнов
    - Последовательной обработки
    - Контроля завершения
    
    Используйте с -Timeout для ограничения времени ожидания.

.PARAMETER Timeout
    Максимальное время ожидания завершения обработки в секундах.
    
    По умолчанию: 300 секунд (5 минут)
    Используется только с флагом -Wait
    
    Статусы завершения:
    - Успех (код 0): task.json.completed создан
    - Ошибка (код 1): task.json.error создан
    - Таймаут (код 2): время истекло
    
    Примеры:
        -Timeout 600   # 10 минут
        -Timeout 1800  # 30 минут

.PARAMETER DebugMode
    Включить режим отладки с детальным выводом информации.
    
    Дополнительный вывод:
    - Загрузка .env файла
    - Пути к файлам и обработке
    - Полная командная строка запуска 1С
    - Детальная информация о процессе
    
    Передается в обработку как: options.debug_mode = true
    Влияет на: Объект.РежимОтладки и создание debug.log

.EXAMPLE
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента.Форма.ФормаДокумента")
    
    Базовое использование: обработать одну форму из файловой базы.

.EXAMPLE
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -FormsFile "forms.txt" -Wait
    
    Обработать список форм из файла с ожиданием завершения.
    Скрипт завершится только после обработки всех форм или таймаута.

.EXAMPLE
    .\form_context_agent.ps1 -InfoBaseName "Production_DB" -UserName "Тестировщик" -Password "Test123" -Forms @("Справочник.Контрагенты.Форма.ФормаЭлемента")
    
    Подключение к клиент-серверной базе с учетными данными.

.EXAMPLE
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента") -IncludeInvisible -DebugMode -NoClose
    
    Режим отладки: включены невидимые элементы, детальный вывод, 1С не закрывается.
    Полезно для диагностики проблем и анализа результатов.

.EXAMPLE
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -FormsFile "all_forms.txt" -Wait -Timeout 1800 -NoMarkdown
    
    Пакетная обработка большого списка форм:
    - Ожидание до 30 минут
    - Только JSON файлы (без Markdown)
    - Подходит для CI/CD

.EXAMPLE
    .\form_context_agent.ps1 -Forms @("Документ.ЗаказКлиента")
    
    Использование параметров из .env файла.
    Требует наличие .env с: V8_PATH, INFOBASE_PATH (или INFOBASE_NAME), USERNAME_1C, PASSWORD_1C

.EXAMPLE
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Справочник.Номенклатура") -V8Path "C:\Program Files\1cv8\8.3.24.1634\bin\1cv8.exe"
    
    Указание конкретной версии платформы 1С.

.EXAMPLE
    # Запуск без ожидания и проверка статуса отдельно
    .\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента")
    
    # Позже проверить статус:
    if (Test-Path "agent\task.json.completed") { Write-Host "Done!" }

.INPUTS
    Нет. Скрипт не принимает данные из конвейера.

.OUTPUTS
    System.Int32
    
    Коды возврата:
    0 - Успешное завершение
    1 - Ошибка (параметры, файлы, запуск)
    2 - Таймаут ожидания (только с -Wait)

.NOTES
    Имя файла: form_context_agent.ps1
    Автор: VA-AI Project
    Требования:
        - PowerShell 5.1 или выше
        - 1C:Enterprise 8.3 (1cv8.exe)
        - FormContextCollector.epf (собрать через build-epf.bat)
    
    Структура файлов:
        form_context_agent.ps1          - Этот скрипт
        FormContextCollector.epf        - Обработка 1С
        agent\task.json                 - Файл задания
        agent\task.json.processing      - Маркер выполнения
        agent\task.json.completed       - Маркер успеха
        agent\task.json.error           - Маркер ошибки
        context\forms\index.json        - Индекс результатов
        context\forms\*.json            - Данные форм
        context\forms\*.md              - Описания форм
        debug.log                       - Лог отладки
    
    Файл .env (опционально):
        V8_PATH=C:\Program Files\1cv8\8.3.24.1634\bin\1cv8.exe
        INFOBASE_PATH=C:\Bases\Production\
        USERNAME_1C=Администратор
        PASSWORD_1C=SecurePassword123
    
    Передача параметров в обработку:
        PowerShell флаг → task.json options → Реквизиты обработки
        -IncludeInvisible → include_invisible → ВключатьНевидимыеЭлементы
        -NoMarkdown → generate_markdown → ГенерироватьMarkdown
        -NoClose → close_after_collection → (управление закрытием)
        -DebugMode → debug_mode → РежимОтладки
    
    Устранение неполадок:
        1. Проверьте debug.log при включенном -DebugMode
        2. Убедитесь что FormContextCollector.epf собран (build-epf.bat)
        3. Проверьте права доступа к каталогу agent\ и context\
        4. При таймауте увеличьте -Timeout или запустите без -Wait

.LINK
    Подробная справка: POWERSHELL_SCRIPT_REFERENCE.md

.LINK
    Руководство: AGENT_MODE_GUIDE.md

.LINK
    Быстрый старт: QUICK_START.md

.LINK
    Проект: https://github.com/your-repo/va-ai
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
    [switch]$NoJson,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoClose,
    
    [Parameter(Mandatory=$false)]
    [switch]$Wait,
    
    [Parameter(Mandatory=$false)]
    [int]$Timeout = 300,
    
    [Parameter(Mandatory=$false)]
    [switch]$DebugMode,
    
    [Parameter(Mandatory=$false)]
    [Alias("h")]
    [switch]$Help
)

# Set encoding
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

#region Help and Quick Start

function Show-QuickHelp {
    Write-Host ""
    Write-Host "Form Context Collector - Agent Mode" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Автоматический сбор контекста форм 1С для AI-ассистентов" -ForegroundColor Gray
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\form_context_agent.ps1 -InfoBasePath [path] -Forms [array]" -ForegroundColor White
    Write-Host "  .\form_context_agent.ps1 -InfoBaseName [name] -FormsFile [file]" -ForegroundColor White
    Write-Host ""
    Write-Host "REQUIRED PARAMETERS:" -ForegroundColor Yellow
    Write-Host "  Database (одно из двух):" -ForegroundColor Gray
    Write-Host "    -InfoBasePath [path]   Путь к файловой базе" -ForegroundColor White
    Write-Host "    -InfoBaseName [name]   Имя базы из списка 1С" -ForegroundColor White
    Write-Host ""
    Write-Host "  Forms (одно из двух):" -ForegroundColor Gray
    Write-Host "    -Forms [array]         Массив путей к формам" -ForegroundColor White
    Write-Host "    -FormsFile [file]      Файл со списком форм" -ForegroundColor White
    Write-Host ""
    Write-Host "COMMON OPTIONS:" -ForegroundColor Yellow
    Write-Host "  -UserName [name]       Имя пользователя 1С" -ForegroundColor White
    Write-Host "  -Password [pwd]        Пароль пользователя" -ForegroundColor White
    Write-Host "  -V8Path [path]         Путь к 1cv8.exe" -ForegroundColor White
    Write-Host "  -IncludeInvisible      Включать невидимые элементы" -ForegroundColor White
    Write-Host "  -NoMarkdown            Не генерировать Markdown (только JSON)" -ForegroundColor White
    Write-Host "  -NoJson                Не генерировать JSON (только Markdown)" -ForegroundColor White
    Write-Host "  -NoClose               Не закрывать 1С после завершения" -ForegroundColor White
    Write-Host "  -Wait                  Ждать завершения обработки" -ForegroundColor White
    Write-Host "  -Timeout [seconds]     Таймаут для -Wait (по умолчанию: 300)" -ForegroundColor White
    Write-Host "  -DebugMode             Режим отладки с детальным выводом" -ForegroundColor White
    Write-Host ""
    Write-Host "EXAMPLES:" -ForegroundColor Yellow
    Write-Host "  # Обработать одну форму" -ForegroundColor Gray
    Write-Host "  .\form_context_agent.ps1 -InfoBasePath ""C:\Bases\Test"" ``" -ForegroundColor White
    Write-Host "      -Forms @(""Документ.ЗаказКлиента.Форма.ФормаДокумента"")" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Обработать список из файла с ожиданием" -ForegroundColor Gray
    Write-Host "  .\form_context_agent.ps1 -InfoBasePath ""C:\Bases\Test"" ``" -ForegroundColor White
    Write-Host "      -FormsFile ""forms.txt"" -Wait" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Режим отладки с невидимыми элементами" -ForegroundColor Gray
    Write-Host "  .\form_context_agent.ps1 -InfoBasePath ""C:\Bases\Test"" ``" -ForegroundColor White
    Write-Host "      -Forms @(""Справочник.Контрагенты"") ``" -ForegroundColor White
    Write-Host "      -IncludeInvisible -DebugMode -NoClose" -ForegroundColor White
    Write-Host ""
    Write-Host "HELP & DOCUMENTATION:" -ForegroundColor Yellow
    Write-Host "  .\form_context_agent.ps1 -Help             Показать эту справку" -ForegroundColor White
    Write-Host "  .\form_context_agent.ps1 -h                То же самое" -ForegroundColor White
    Write-Host "  Get-Help .\form_context_agent.ps1          Краткая справка" -ForegroundColor White
    Write-Host "  Get-Help .\form_context_agent.ps1 -Detailed    Детальная справка" -ForegroundColor White
    Write-Host "  Get-Help .\form_context_agent.ps1 -Examples    Примеры использования" -ForegroundColor White
    Write-Host "  Get-Help .\form_context_agent.ps1 -Full        Полная справка" -ForegroundColor White
    Write-Host ""
    Write-Host "  POWERSHELL_SCRIPT_REFERENCE.md - Полная справочная документация" -ForegroundColor White
    Write-Host "  AGENT_MODE_GUIDE.md            - Руководство по агентскому режиму" -ForegroundColor White
    Write-Host "  QUICK_START.md                 - Быстрый старт" -ForegroundColor White
    Write-Host ""
}

# Check for help flag (-Help, -h, -?)
if ($Help) {
    Show-QuickHelp
    Write-Host "Для детальной справки используйте:" -ForegroundColor Cyan
    Write-Host "  Get-Help .\form_context_agent.ps1 -Detailed" -ForegroundColor White
    Write-Host ""
    exit 0
}

# Also check for common help variations in direct arguments
$helpArgs = @("-h", "--help", "-help", "/?", "/h", "/help", "help")
foreach ($arg in $args) {
    if ($helpArgs -contains $arg.ToLower()) {
        Show-QuickHelp
        Write-Host "Для детальной справки используйте:" -ForegroundColor Cyan
        Write-Host "  Get-Help .\form_context_agent.ps1 -Detailed" -ForegroundColor White
        Write-Host ""
        exit 0
    }
}

# Check if script was called without any parameters - show quick help
if ($PSBoundParameters.Count -eq 0 -and $args.Count -eq 0) {
    Show-QuickHelp
    Write-Host "ERROR: " -NoNewline -ForegroundColor Red
    Write-Host "Скрипт запущен без параметров" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Check if script was called without required parameters - show quick help
$hasInfoBase = $InfoBasePath -or $InfoBaseName
$hasForms = $Forms -or $FormsFile

if (-not $hasInfoBase -or -not $hasForms) {
    # Check if .env might have the values
    $envFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".env"
    $hasEnvFile = Test-Path $envFile
    
    # If no .env file or still missing forms, show quick help
    if (-not $hasEnvFile -or -not $hasForms) {
        Show-QuickHelp
        # Don't exit yet - let the validation section handle it with proper error messages
    }
}

#endregion

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
                    # Remove quotes from values
                    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                        $value = $value.Substring(1, $value.Length - 2)
                    }
                    elseif ($value.StartsWith("'") -and $value.EndsWith("'")) {
                        $value = $value.Substring(1, $value.Length - 2)
                    }
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
    generate_json = -not $NoJson.IsPresent
    max_depth = 5
    close_after_collection = -not $NoClose.IsPresent
    wait_form_timeout = 2000
    debug_mode = $DebugMode.IsPresent
}

Write-Host "Settings:" -ForegroundColor Green
Write-Host "   Include invisible: $($options.include_invisible)"
Write-Host "   Generate Markdown: $($options.generate_markdown)"
Write-Host "   Generate JSON: $($options.generate_json)"
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
