# Changelog: Добавление параметра отключения генерации JSON

## Дата: 2025-11-30

## Изменения

### 1. PowerShell скрипт (`form_context_agent.ps1`)

Добавлен новый параметр `-NoJson`:

```powershell
.\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента") -NoJson
```

- **По умолчанию**: JSON **НЕ генерируется** (создается только MD)
- Для включения генерации JSON: **не указывать** флаг `-NoJson`
- Параметр передается в `task.json` как `options.generate_json`

### 2. Обработка 1С (`FormContextCollector`)

#### Новый реквизит
- **Имя**: `ГенерироватьJSON`
- **Тип**: Булево
- **По умолчанию**: `Ложь` (только MD файлы)
- **Отображение**: Чекбокс на форме обработки

#### Измененные методы

**`ПриСозданииНаСервере()`**
```bsl
Объект.ГенерироватьJSON = Ложь; // По умолчанию только MD
```

**`СобратьКонтекст()` (интерактивный режим)**
```bsl
Если Объект.ГенерироватьJSON Тогда
    // Генерация и сохранение JSON
    ТекстJSON = ПреобразоватьВJSON(ДанныеФормы);
    СохранитьВФайл(ТекстJSON, ПутьJSON);
Иначе
    ИмяФайлаJSON = ""; // Не создаем JSON
    Лог("Генерация JSON отключена");
КонецЕсли;
```

**`СобратьКонтекстОткрытойФормыАгента()` (агентский режим)**
```bsl
ИмяФайлаJSON = "";
Если Объект.ГенерироватьJSON Тогда
    ТекстJSON = ПреобразоватьВJSON(ДанныеФормы);
    ИмяФайлаJSON = СформироватьИмяФайла(...) + ".json";
    СохранитьВФайл(ТекстJSON, ПутьJSON);
Иначе
    Лог("Генерация JSON отключена");
КонецЕсли;
```

**`ПрименитьНастройкиЗадания()`**
```bsl
Если Опции.Свойство("generate_json") Тогда
    Объект.ГенерироватьJSON = Опции.generate_json;
    Лог(СтрШаблон("  - Генерировать JSON: %1", Опции.generate_json));
КонецЕсли;
```

**`ОбновитьИндексФорм()`**
```bsl
// Добавляем путь к JSON только если он создан
Если Не ПустаяСтрока(ИмяФайлаJSON) Тогда
    ЗаписьФормы.Вставить("json_path", ИмяФайлаJSON);
КонецЕсли;
```

### 3. Файл задания (`agent/task.json.example`)

```json
{
  "options": {
    "include_invisible": false,
    "generate_markdown": true,
    "generate_json": false,    // <-- Новый параметр (по умолчанию false)
    "max_depth": 5,
    "close_after_collection": true,
    "wait_form_timeout": 2000
  }
}
```

## Поведение по умолчанию

### Было (старое поведение)
- Всегда генерировались **оба** формата: JSON + MD
- Нельзя было отключить JSON

### Стало (новое поведение)
- **По умолчанию**: только **MD файлы**
- JSON генерируется **только** если:
  - В PowerShell скрипте **не указан** флаг `-NoJson`
  - В `task.json` установлено `"generate_json": true`
  - В интерактивном режиме установлен чекбокс "Генерировать JSON"

## Примеры использования

### PowerShell

```powershell
# Только MD (по умолчанию)
.\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента")

# Только JSON (без MD)
.\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента") -NoMarkdown

# Оба формата
.\form_context_agent.ps1 -InfoBasePath "C:\Bases\Test" -Forms @("Документ.ЗаказКлиента")
# (не указываем ни -NoJson, ни -NoMarkdown)
```

### task.json

```json
// Только MD
{
  "options": {
    "generate_markdown": true,
    "generate_json": false
  }
}

// Только JSON
{
  "options": {
    "generate_markdown": false,
    "generate_json": true
  }
}

// Оба формата
{
  "options": {
    "generate_markdown": true,
    "generate_json": true
  }
}
```

## Обратная совместимость

- Если в `task.json` отсутствует `generate_json`, используется значение **false** (только MD)
- Старые скрипты без флага `-NoJson` будут генерировать только MD (изменение поведения!)
- Для восстановления старого поведения (оба формата) нужно **не указывать** флаги `-NoJson` и `-NoMarkdown`

## Файлы изменены

1. `form_context_agent.ps1` - добавлен параметр `-NoJson`
2. `src/FormContextCollector.xml` - добавлен реквизит `ГенерироватьJSON`
3. `src/FormContextCollector/Forms/Форма/Ext/Form.xml` - добавлен чекбокс
4. `src/FormContextCollector/Forms/Форма/Ext/Form/Module.bsl` - логика обработки
5. `agent/task.json.example` - обновлен пример

## Необходимые действия после внедрения

1. Пересобрать EPF: `build-epf.bat`
2. Обновить документацию (README, QUICK_START и т.д.)
3. Протестировать все режимы:
   - Интерактивный (с галочкой и без)
   - Агентский с `generate_json: true`
   - Агентский с `generate_json: false`
   - PowerShell с разными комбинациями флагов

