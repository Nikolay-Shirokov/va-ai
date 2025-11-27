@echo off
REM Скрипт для валидации сценариев Vanessa Automation (Windows)
REM Использование: validate.bat <путь_к_файлу.feature> [опции]

python tools\validator\validate.py %* --ai-format