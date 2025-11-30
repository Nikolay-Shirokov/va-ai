@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem Скрипт сборки EPF-файла обработки из исходников XML
rem ============================================================
rem Использует команду /LoadExternalDataProcessorOrReportFromFiles
rem Документация: Приложение 7, раздел 7.4.8

echo.
echo ========================================
echo Сборка FormContextCollector.epf
echo ========================================
echo.

rem --- Настройки ---
set "SCRIPT_DIR=%~dp0"
set "SRC_DIR=%SCRIPT_DIR%dev\src"
set "OUTPUT_FILE=%SCRIPT_DIR%FormContextCollector.epf"
set "TEMP_IB=%SCRIPT_DIR%agent\temp_ib"
set "LOG_FILE=%SCRIPT_DIR%agent\build.log"

rem --- Поиск 1cv8.exe ---
echo [1/5] Поиск 1cv8.exe...

rem Проверяем стандартные пути установки
set "V8_EXE="

if exist "C:\Program Files\1cv8\8.3.24.1667\bin\1cv8.exe" set "V8_EXE=C:\Program Files\1cv8\8.3.24.1667\bin\1cv8.exe" & goto :found_v8
if exist "C:\Program Files\1cv8\8.3.23\bin\1cv8.exe" set "V8_EXE=C:\Program Files\1cv8\8.3.23\bin\1cv8.exe" & goto :found_v8
if exist "C:\Program Files\1cv8\8.3.22\bin\1cv8.exe" set "V8_EXE=C:\Program Files\1cv8\8.3.22\bin\1cv8.exe" & goto :found_v8
if exist "C:\Program Files\1cv8\common\1cestart.exe" set "V8_EXE=C:\Program Files\1cv8\common\1cestart.exe" & goto :found_v8
if exist "C:\Program Files (x86)\1cv8\8.3.24.1667\bin\1cv8.exe" set "V8_EXE=C:\Program Files (x86)\1cv8\8.3.24.1667\bin\1cv8.exe" & goto :found_v8
if exist "C:\Program Files (x86)\1cv8\8.3.23\bin\1cv8.exe" set "V8_EXE=C:\Program Files (x86)\1cv8\8.3.23\bin\1cv8.exe" & goto :found_v8
if exist "C:\Program Files (x86)\1cv8\common\1cestart.exe" set "V8_EXE=C:\Program Files (x86)\1cv8\common\1cestart.exe" & goto :found_v8

echo ОШИБКА: 1cv8.exe не найден!
echo.
echo Проверено:
echo   - C:\Program Files\1cv8\
echo   - C:\Program Files (x86)\1cv8\
echo.
echo Установите платформу 1С:Предприятие 8.3
echo Или укажите путь вручную, отредактировав скрипт
exit /b 1

:found_v8
echo    Найдено: %V8_EXE%
echo.

rem --- Проверка исходников ---
echo [2/5] Проверка исходников...

if not exist "%SRC_DIR%\FormContextCollector.xml" (
    echo ОШИБКА: Не найден файл FormContextCollector.xml
    echo Путь: %SRC_DIR%
    exit /b 1
)

echo    Найдено: FormContextCollector.xml
echo    Найдено: FormContextCollector\Ext\ObjectModule.bsl
echo    Найдено: FormContextCollector\Forms\Форма\...
echo.

rem --- Подготовка временной ИБ ---
echo [3/5] Подготовка временной информационной базы...

rem Создаём каталог agent если его нет
if not exist "%SCRIPT_DIR%agent" (
    mkdir "%SCRIPT_DIR%agent"
)

rem Удаляем старую временную ИБ если есть
if exist "%TEMP_IB%" (
    rmdir /S /Q "%TEMP_IB%" 2>nul
)

rem Создаём новую пустую ИБ
mkdir "%TEMP_IB%"

echo    Создана: %TEMP_IB%
echo.

rem --- Удаление старого EPF ---
echo [4/5] Подготовка выходного файла...

if exist "%OUTPUT_FILE%" (
    del /F /Q "%OUTPUT_FILE%" 2>nul
    if exist "%OUTPUT_FILE%" (
        echo ОШИБКА: Не удалось удалить старый файл %OUTPUT_FILE%
        echo Возможно, файл используется другим процессом
        exit /b 1
    )
    echo    Удалён старый файл
)
echo.

rem --- Сборка EPF ---
echo [5/5] Сборка EPF-файла...
echo.

rem Формируем команду
rem Синтаксис: /LoadExternalDataProcessorOrReportFromFiles <корневой каталог> <выходной файл>
set "CMD="%V8_EXE%" CREATEINFOBASE File="%TEMP_IB%";DBFormat=8.3.8"
set "CMD=%CMD% /DisableStartupDialogs /Out "%LOG_FILE%""

echo    Создание ИБ...
%CMD% >nul 2>&1

if errorlevel 1 (
    echo ОШИБКА: Не удалось создать временную ИБ
    echo Смотрите лог: %LOG_FILE%
    exit /b 1
)

rem Команда сборки
rem Синтаксис: /LoadExternalDataProcessorOrReportFromFiles <корневой XML-файл> <выходной EPF>
set "CMD="%V8_EXE%" DESIGNER /F "%TEMP_IB%""
set "CMD=%CMD% /LoadExternalDataProcessorOrReportFromFiles "%SRC_DIR%\FormContextCollector.xml" "%OUTPUT_FILE%""
set "CMD=%CMD% /DisableStartupDialogs /Out "%LOG_FILE%""

echo    Выполнение LoadExternalDataProcessorOrReportFromFiles...
echo.

%CMD%

if errorlevel 1 (
    echo.
    echo ОШИБКА: Сборка завершилась с ошибкой!
    echo.
    echo === Лог сборки ===
    if exist "%LOG_FILE%" (
        type "%LOG_FILE%"
    ) else (
        echo Лог-файл не создан
    )
    echo ==================
    echo.
    goto :cleanup
)

rem --- Проверка результата ---
if not exist "%OUTPUT_FILE%" (
    echo.
    echo ОШИБКА: Файл %OUTPUT_FILE% не создан!
    echo.
    echo === Лог сборки ===
    if exist "%LOG_FILE%" (
        type "%LOG_FILE%"
    ) else (
        echo Лог-файл не создан
    )
    echo ==================
    echo.
    goto :cleanup
)

rem Получаем размер файла
for %%F in ("%OUTPUT_FILE%") do set "FILE_SIZE=%%~zF"

echo ========================================
echo УСПЕШНО!
echo ========================================
echo.
echo Создан: %OUTPUT_FILE%
echo Размер: %FILE_SIZE% байт
echo.

if exist "%LOG_FILE%" (
    echo Лог: %LOG_FILE%
)

echo.
echo Теперь вы можете:
echo 1. Открыть EPF в конфигураторе для проверки
echo 2. Загрузить EPF в рабочую базу
echo 3. Использовать в Vanessa Automation
echo.

:cleanup
rem --- Очистка ---
if exist "%TEMP_IB%" (
    rmdir /S /Q "%TEMP_IB%" 2>nul
)

echo.
pause