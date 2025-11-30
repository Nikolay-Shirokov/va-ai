# Справка по использованию form_context_agent.ps1

## Быстрый вызов справки

### Все варианты вызова справки

```powershell
# PowerShell флаг
.\form_context_agent.ps1 -Help

# Короткие варианты
.\form_context_agent.ps1 -h
.\form_context_agent.ps1 --help

# Windows стиль
.\form_context_agent.ps1 /?
.\form_context_agent.ps1 /help

# Прямая команда
.\form_context_agent.ps1 help
```

### Встроенная PowerShell справка

```powershell
# Краткая справка
Get-Help .\form_context_agent.ps1

# Детальная справка (рекомендуется)
Get-Help .\form_context_agent.ps1 -Detailed

# Только примеры
Get-Help .\form_context_agent.ps1 -Examples

# Полная справка
Get-Help .\form_context_agent.ps1 -Full

# Справка по параметру
Get-Help .\form_context_agent.ps1 -Parameter Forms
Get-Help .\form_context_agent.ps1 -Parameter Wait
```

## Запуск без параметров

При запуске без обязательных параметров отображается краткая справка:

```powershell
# Просто запустить скрипт
.\form_context_agent.ps1
```

Выведет:
```
Form Context Collector - Agent Mode
============================================================

USAGE:
  .\form_context_agent.ps1 -InfoBasePath <path> -Forms <array>
  .\form_context_agent.ps1 -InfoBaseName <name> -FormsFile <file>

REQUIRED PARAMETERS:
  Database:
    -InfoBasePath <path>   Path to file infobase
      OR
    -InfoBaseName <name>   Name from infobase list

  Forms:
    -Forms <array>         Array of form paths
      OR
    -FormsFile <file>      File with forms list

COMMON OPTIONS:
  -IncludeInvisible      Include invisible elements
  -NoMarkdown            Don't generate Markdown files
  -NoClose               Don't close 1C after collection
  -Wait                  Wait for completion
  -Timeout <seconds>     Timeout for -Wait (default: 300)
  -DebugMode             Enable debug output

EXAMPLES:
  ...
```

## Минимальные примеры запуска

### Одна форма

```powershell
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -Forms @("Документ.ЗаказКлиента.Форма.ФормаДокумента")
```

### Из файла

```powershell
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -FormsFile "forms.txt"
```

### С ожиданием

```powershell
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -Forms @("Документ.ЗаказКлиента") `
    -Wait
```

### Режим отладки

```powershell
.\form_context_agent.ps1 `
    -InfoBasePath "C:\Bases\Test" `
    -Forms @("Документ.ЗаказКлиента") `
    -DebugMode `
    -NoClose
```

## Документация

- **POWERSHELL_SCRIPT_REFERENCE.md** - Полная справка по всем параметрам и примерам
- **AGENT_MODE_GUIDE.md** - Руководство по агентскому режиму
- **QUICK_START.md** - Быстрый старт
- **TROUBLESHOOTING.md** - Устранение неполадок

## Интерактивная справка

```powershell
# Справка в отдельном окне (если настроено)
Get-Help .\form_context_agent.ps1 -ShowWindow

# Справка в браузере (если настроена ссылка)
Get-Help .\form_context_agent.ps1 -Online
```

