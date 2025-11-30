# Form Context Agent - Справка по PowerShell скрипту

## Описание

`form_context_agent.ps1` - PowerShell скрипт для автоматического сбора контекста форм 1С для AI-ассистентов.

Скрипт создает файл задания `task.json`, запускает 1С с обработкой `FormContextCollector.epf` и опционально ожидает завершения обработки.

## Синтаксис

```powershell
.\form_context_agent.ps1 
    [-InfoBasePath <String>]
    [-InfoBaseName <String>]
    [-UserName <String>]
    [-Password <String>]
    [-Forms <String[]>]
    [-FormsFile <String>]
    [-V8Path <String>]
    [-IncludeInvisible]
    [-NoMarkdown]
    [-NoClose]
    [-Wait]
    [-Timeout <Int32>]
    [-DebugMode]
```

## Параметры

### Подключение к базе данных

#### `-InfoBasePath <String>`
Путь к файловой базе данных 1С.

- **Формат**: `C:\Bases\MyBase\` или просто `C:\Bases\MyBase`
- **Обязательный**: Нет (если указан `-InfoBaseName`)
- **Из .env**: `INFOBASE_PATH`

**Пример:**
```powershell
-InfoBasePath "C:\Bases\Production\"
```

#### `-InfoBaseName <String>`
Имя базы данных из списка информационных баз 1С (для клиент-серверных баз или зарегистрированных файловых).

- **Обязательный**: Нет (если указан `-InfoBasePath`)
- **Из .env**: `INFOBASE_NAME`

**Пример:**
```powershell
-InfoBaseName "Production_Database"
```

#### `-UserName <String>`
Имя пользователя 1С для подключения.

- **Обязательный**: Нет
- **Из .env**: `USERNAME_1C`

**Пример:**
```powershell
-UserName "Администратор"
```

#### `-Password <String>`
Пароль пользователя 1С.

- **Обязательный**: Нет
- **Из .env**: `PASSWORD_1C`

**Пример:**
```powershell
-Password "SecurePassword123"
```

### Формы для обработки

#### `-Forms <String[]>`
Массив путей к формам для обработки.

- **Формат**: Массив строк вида `"Тип.ИмяОбъекта.Форма.ИмяФормы"`
- **Обязательный**: Да (если не указан `-FormsFile`)

**Примеры:**
```powershell
# Одна форма
-Forms @("Документ.ЗаказКлиента.Форма.ФормаДокумента")

# Несколько форм
-Forms @(
    "Документ.ЗаказКлиента.Форма.ФормаДокумента",
    "Справочник.Контрагенты.Форма.ФормаЭлемента"
)
```

#### `-FormsFile <String>`
Путь к текстовому файлу со списком форм (по одной на строку).

- **Формат файла**: UTF-8, одна форма на строку, строки с `#` игнорируются
- **Обязательный**: Да (если не указан `-Forms`)

**Пример файла `forms.txt`:**
```
# Документы
Документ.ЗаказКлиента.Форма.ФормаДокумента
Документ.РеализацияТоваров.Форма.ФормаДокумента

# Справочники
Справочник.Контрагенты.Форма.ФормаЭлемента
Справочник.Номенклатура.Форма.ФормаЭлемента
```

**Использование:**
```powershell
-FormsFile "forms.txt"
```

### Платформа 1С

#### `-V8Path <String>`
Путь к исполняемому файлу платформы 1С (`1cv8.exe`).

- **По умолчанию**: `1cv8.exe` (из PATH)
- **Из .env**: `V8_PATH`

**Примеры:**
```powershell
# Полный путь
-V8Path "C:\Program Files\1cv8\8.3.24.1634\bin\1cv8.exe"

# Из PATH
-V8Path "1cv8.exe"
```

### Управляющие флаги

#### `-IncludeInvisible`
Включать невидимые элементы формы в результаты сбора.

- **Тип**: Switch (флаг)
- **По умолчанию**: Отключено
- **Передается в обработку**: Да (`options.include_invisible`)

**Пример:**
```powershell
-IncludeInvisible
```

#### `-NoMarkdown`
Отключить генерацию Markdown-файлов с описанием форм.

- **Тип**: Switch (флаг)
- **По умолчанию**: Markdown генерируется
- **Передается в обработку**: Да (`options.generate_markdown`)

**Пример:**
```powershell
-NoMarkdown  # Только JSON, без .md файлов
```

#### `-NoClose`
Не закрывать 1С после завершения обработки.

- **Тип**: Switch (флаг)
- **По умолчанию**: 1С закрывается автоматически
- **Передается в обработку**: Да (`options.close_after_collection`)

**Пример:**
```powershell
-NoClose  # 1С останется открытой для просмотра
```

### Режимы ожидания

#### `-Wait`
Ждать завершения обработки перед выходом из скрипта.

- **Тип**: Switch (флаг)
- **По умолчанию**: Скрипт завершается сразу после запуска 1С

**Пример:**
```powershell
-Wait  # Скрипт дождется завершения или таймаута
```

#### `-Timeout <Int32>`
Таймаут ожидания завершения обработки в секундах (используется с `-Wait`).

- **По умолчанию**: 300 (5 минут)
- **Минимум**: Не ограничен
- **Только с**: `-Wait`

**Пример:**
```powershell
-Wait -Timeout 600  # Ждать до 10 минут
```

### Отладка

#### `-DebugMode`
Режим отладки с дополнительным выводом информации.

- **Тип**: Switch (флаг)
- **Передается в обработку**: Да (`options.debug_mode`)
- **Дополнительно**: Выводит команду запуска 1С

**Пример:**
```powershell
-DebugMode
```

## Файл .env

Скрипт автоматически загружает переменные окружения из файла `.env` в каталоге скрипта.

**Формат `.env`:**
```ini
# Путь к платформе 1С
V8_PATH=C:\Program Files\1cv8\8.3.24.1634\bin\1cv8.exe

# База данных
INFOBASE_PATH=C:\Bases\Production\
# или
INFOBASE_NAME=Production_Database

# Учетные данные
USERNAME_1C=Администратор
PASSWORD_1C=SecurePassword123
```

**Приоритет параметров**: Параметры командной строки > `.env` > Значения по умолчанию

## Примеры использования

### Базовое использование

```powershell
# Обработать одну форму
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -Forms @("Документ.ЗаказКлиента.Форма.ФормаДокумента")
```

### Обработка нескольких форм из файла

```powershell
# С ожиданием завершения
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -FormsFile "forms.txt" `
    -Wait `
    -Timeout 600
```

### Клиент-серверная база с учетными данными

```powershell
.\form_context_agent.ps1 `
    -InfoBaseName "Production_DB" `
    -UserName "Тестировщик" `
    -Password "Test123" `
    -Forms @("Справочник.Контрагенты.Форма.ФормаЭлемента")
```

### Режим отладки с невидимыми элементами

```powershell
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -Forms @("Документ.ЗаказКлиента.Форма.ФормаДокумента") `
    -IncludeInvisible `
    -DebugMode `
    -NoClose
```

### Использование .env файла

**Файл `.env`:**
```ini
V8_PATH=C:\Program Files\1cv8\8.3.24.1634\bin\1cv8.exe
INFOBASE_PATH=C:\Bases\Test\
USERNAME_1C=Администратор
```

**Команда:**
```powershell
# Параметры из .env, только формы указываем
.\form_context_agent.ps1 -Forms @("Документ.ЗаказКлиента")
```

### Пакетная обработка с фоновым запуском

```powershell
# Запустить и сразу выйти
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -FormsFile "all_forms.txt"

# Проверить статус позже:
# task.json.processing - в процессе
# task.json.completed - завершено
# task.json.error - ошибка
```

### Только JSON без Markdown

```powershell
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -Forms @("Справочник.Контрагенты") `
    -NoMarkdown
```

## Передаваемые параметры в обработку

Скрипт создает файл `agent\task.json` со следующей структурой:

```json
{
  "version": "1.0",
  "mode": "agent",
  "forms": [
    {
      "type": "form_path",
      "value": "Документ.ЗаказКлиента.Форма.ФормаДокумента"
    }
  ],
  "options": {
    "include_invisible": false,
    "generate_markdown": true,
    "max_depth": 5,
    "close_after_collection": true,
    "wait_form_timeout": 2000,
    "debug_mode": false
  }
}
```

### Соответствие параметров

| PowerShell параметр | JSON поле | Обработка 1С |
|---------------------|-----------|--------------|
| `-IncludeInvisible` | `options.include_invisible` | `Объект.ВключатьНевидимыеЭлементы` |
| `-NoMarkdown` | `options.generate_markdown` | `Объект.ГенерироватьMarkdown` |
| `-NoClose` | `options.close_after_collection` | Управление закрытием |
| `-DebugMode` | `options.debug_mode` | `Объект.РежимОтладки` |
| - | `options.max_depth` | `Объект.МаксимальнаяГлубинаВложенности` |
| - | `options.wait_form_timeout` | Таймаут ожидания открытия формы |

## Результаты работы

### Файлы статуса

- `agent\task.json` - Исходное задание (создается скриптом)
- `agent\task.json.processing` - Обработка в процессе (создается обработкой)
- `agent\task.json.completed` - Успешное завершение (создается обработкой)
- `agent\task.json.error` - Ошибка при обработке (создается обработкой)

### Выходные файлы

- `context\forms\index.json` - Индекс всех обработанных форм
- `context\forms\<ТипОбъекта>.<ИмяОбъекта>.Форма.<ИмяФормы>.json` - JSON с данными формы
- `context\forms\<ТипОбъекта>.<ИмяОбъекта>.Форма.<ИмяФормы>.md` - Markdown описание (если не `-NoMarkdown`)

### Логи

- `debug.log` - Детальный лог работы обработки (если `-DebugMode`)

## Коды возврата

| Код | Значение | Условие |
|-----|----------|---------|
| 0 | Успех | Обработка завершена успешно (при `-Wait`) или 1С запущена (без `-Wait`) |
| 1 | Ошибка | Ошибка параметров, файлов или запуска 1С |
| 2 | Таймаут | Превышен таймаут ожидания (при `-Wait`) |

## Проверка статуса без ожидания

```powershell
# Запустить без ожидания
.\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента")

# Проверить статус
$taskDir = ".\agent"
if (Test-Path "$taskDir\task.json.completed") {
    Write-Host "Completed!" -ForegroundColor Green
} elseif (Test-Path "$taskDir\task.json.error") {
    Write-Host "Error!" -ForegroundColor Red
} elseif (Test-Path "$taskDir\task.json.processing") {
    Write-Host "Processing..." -ForegroundColor Yellow
} else {
    Write-Host "Waiting for start..." -ForegroundColor Cyan
}
```

## Устранение неполадок

### 1С не найдена

```
ERROR: 1C:Enterprise platform (1cv8.exe) not found
```

**Решение:**
- Укажите полный путь через `-V8Path`
- Добавьте `V8_PATH` в `.env`
- Добавьте `1cv8.exe` в PATH

### Обработка не найдена

```
ERROR: Processing not found: ...\FormContextCollector.epf
```

**Решение:**
```powershell
cd tools\form-context
.\build-epf.bat
```

### Таймаут ожидания

```
WARNING: Timeout exceeded
```

**Решение:**
- Увеличьте таймаут: `-Timeout 600`
- Проверьте `debug.log` на ошибки
- Запустите с `-DebugMode` для диагностики

### Формы не обрабатываются

**Проверка:**
1. Убедитесь, что файл `task.json` создан
2. Проверьте логи в `debug.log`
3. Запустите с `-DebugMode` и `-NoClose`
4. Проверьте правильность путей к формам

## Интеграция с CI/CD

```powershell
# Пример для Azure DevOps / GitHub Actions
$exitCode = 0

.\form_context_agent.ps1 `
    -InfoBasePath "$(Build.SourcesDirectory)\TestBase" `
    -FormsFile "forms_to_test.txt" `
    -Wait `
    -Timeout 600 `
    -DebugMode

if ($LASTEXITCODE -ne 0) {
    Write-Error "Form context collection failed"
    exit $LASTEXITCODE
}

# Проверка результатов
$indexFile = "context\forms\index.json"
if (-not (Test-Path $indexFile)) {
    Write-Error "Index file not created"
    exit 1
}

Write-Host "Context collection completed successfully"
```

## См. также

- [AGENT_MODE_GUIDE.md](AGENT_MODE_GUIDE.md) - Подробное руководство по агентскому режиму
- [QUICK_START.md](QUICK_START.md) - Быстрый старт
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Устранение неполадок

## Получение справки

```powershell
# Встроенная справка PowerShell
Get-Help .\form_context_agent.ps1
Get-Help .\form_context_agent.ps1 -Detailed
Get-Help .\form_context_agent.ps1 -Examples
Get-Help .\form_context_agent.ps1 -Full
```

