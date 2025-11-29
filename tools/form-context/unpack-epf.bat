@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem Скрипт разборки EPF-файла в исходники XML
rem ============================================================
rem Использует команду /DumpExternalDataProcessorOrReportToFiles
rem Документация: Приложение 7, раздел 7.4.8

echo.
echo ========================================
echo Разборка FormContextCollector.epf
echo ========================================
echo.

rem --- Настройки ---
set "SCRIPT_DIR=%~dp0"
set "EPF_FILE=%SCRIPT_DIR%FormContextCollector.epf"
set "OUTPUT_DIR=%SCRIPT_DIR%src"
set "TEMP_IB=%SCRIPT_DIR%agent\temp_ib"
set "LOG_FILE=%SCRIPT_DIR%agent\unpack.log"

rem --- Проверка входного файла ---
echo [1/4] Проверка EPF-файла...

if not exist "%EPF_FILE%" (
    echo ОШИБКА: Файл не найден: %EPF_FILE%
    echo.
    echo Сначала создайте EPF используя build-epf.bat
    exit /b 1
)

for %%F in ("%EPF_FILE%") do set "FILE_SIZE=%%~zF"
echo    Найдено: FormContextCollector.epf
echo    Размер: %FILE_SIZE% байт
echo.

rem --- Поиск 1cv8.exe ---
echo [2/4] Поиск 1cv8.exe...

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
echo Установите платформу 1С:Предприятие 8.3
exit /b 1

:found_v8
echo    Найдено: %V8_EXE%
echo.

rem --- Подготовка ---
echo [3/4] Подготовка...

if not exist "%SCRIPT_DIR%agent" (
    mkdir "%SCRIPT_DIR%agent"
)

if exist "%TEMP_IB%" (
    rmdir /S /Q "%TEMP_IB%" 2>nul
)
mkdir "%TEMP_IB%"

rem Очищаем целевой каталог (спрашиваем подтверждение)
if exist "%OUTPUT_DIR%" (
    echo.
    echo ВНИМАНИЕ: Каталог %OUTPUT_DIR% будет очищен!
    echo.
    choice /C YN /M "Продолжить"
    if errorlevel 2 (
        echo Отменено пользователем
        exit /b 0
    )
    
    rmdir /S /Q "%OUTPUT_DIR%" 2>nul
)

mkdir "%OUTPUT_DIR%"
echo    Подготовлено: %OUTPUT_DIR%
echo.

rem --- Создание временной ИБ ---
set "CMD="%V8_EXE%" CREATEINFOBASE File="%TEMP_IB%";DBFormat=8.3.8"
set "CMD=%CMD% /DisableStartupDialogs /Out "%LOG_FILE%""

%CMD% >nul 2>&1

if errorlevel 1 (
    echo ОШИБКА: Не удалось создать временную ИБ
    exit /b 1
)

rem --- Разборка EPF ---
echo [4/4] Разборка EPF в XML...
echo.

rem Синтаксис: /DumpExternalDataProcessorOrReportToFiles <корневой XML-файл> <EPF-файл> [-Format Hierarchical]
set "ROOT_XML=%OUTPUT_DIR%\FormContextCollector.xml"
set "CMD="%V8_EXE%" DESIGNER /F "%TEMP_IB%""
set "CMD=%CMD% /DumpExternalDataProcessorOrReportToFiles "%ROOT_XML%" "%EPF_FILE%" -Format Hierarchical"
set "CMD=%CMD% /DisableStartupDialogs /Out "%LOG_FILE%""

%CMD%

if errorlevel 1 (
    echo.
    echo ОШИБКА: Разборка завершилась с ошибкой!
    echo.
    echo === Лог разборки ===
    if exist "%LOG_FILE%" (
        type "%LOG_FILE%"
    )
    echo ====================
    echo.
    goto :cleanup
)

rem --- Проверка результата ---
if not exist "%ROOT_XML%" (
    echo.
    echo ОШИБКА: Файлы не созданы!
    echo.
    if exist "%LOG_FILE%" (
        echo === Лог разборки ===
        type "%LOG_FILE%"
        echo ====================
    )
    echo.
    goto :cleanup
)

echo ========================================
echo УСПЕШНО!
echo ========================================
echo.
echo Исходники сохранены в: %OUTPUT_DIR%
echo.
echo Структура:
dir /S /B "%OUTPUT_DIR%" | findstr /V "\.git"
echo.

:cleanup
if exist "%TEMP_IB%" (
    rmdir /S /Q "%TEMP_IB%" 2>nul
)

echo.
pause