#!/usr/bin/env python3
"""
Form Context Collector - CLI для агентского режима
Версия: 1.0

Использование:
    python form_context_cli.py agent --infobase "File=C:/Bases/Test/" --forms "Документ.ЗаказПокупателя"
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional


def create_task_file(forms: List[Dict], options: Dict) -> Path:
    """
    Создает управляющий файл task.json
    
    Args:
        forms: Список форм для обработки
        options: Настройки обработки
        
    Returns:
        Path: Путь к созданному task.json
    """
    task = {
        "version": "1.0",
        "mode": "agent",
        "forms": forms,
        "options": options
    }
    
    # Путь к task.json
    script_dir = Path(__file__).parent
    task_file = script_dir / "agent" / "task.json"
    
    # Создаем директорию если нужно
    task_file.parent.mkdir(exist_ok=True)
    
    # Записываем JSON
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Создан файл задания: {task_file}")
    return task_file


def launch_1c(infobase: str, processing_path: Path, wait: bool = False) -> bool:
    """
    Запускает 1С с обработкой
    
    Args:
        infobase: Строка подключения к базе
        processing_path: Путь к обработке
        wait: Ждать завершения процесса
        
    Returns:
        bool: True если запуск успешен
    """
    cmd = [
        "1cv8",
        "ENTERPRISE",
        f"/F{infobase}",
        f"/Execute{processing_path}",
    ]
    
    print(f"\n🚀 Запуск 1С...")
    print(f"  База: {infobase}")
    print(f"  Обработка: {processing_path}")
    
    try:
        if wait:
            # Ждем завершения
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        else:
            # Запускаем в фоне
            subprocess.Popen(cmd)
            return True
    except FileNotFoundError:
        print("❌ ОШИБКА: 1cv8 не найден в PATH", file=sys.stderr)
        print("   Убедитесь, что 1С установлен и добавлен в PATH", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ ОШИБКА запуска: {e}", file=sys.stderr)
        return False


def wait_for_completion(task_file: Path, timeout: int = 300) -> str:
    """
    Ожидает завершения обработки
    
    Args:
        task_file: Путь к task.json
        timeout: Таймаут ожидания в секундах
        
    Returns:
        str: Статус завершения: "completed", "error", "timeout"
    """
    print(f"\n⏳ Ожидание завершения (таймаут: {timeout}с)...")
    
    start_time = time.time()
    processing_file = task_file.with_suffix('.json.processing')
    completed_file = task_file.with_suffix('.json.completed')
    error_file = task_file.with_suffix('.json.error')
    
    # Ждем пока появится .processing
    print("   Ожидание начала обработки...", end='', flush=True)
    while not processing_file.exists() and (time.time() - start_time) < 30:
        time.sleep(0.5)
        print('.', end='', flush=True)
    print()
    
    if not processing_file.exists():
        print("⚠️  ПРЕДУПРЕЖДЕНИЕ: файл .processing не появился")
        return "timeout"
    
    print("   ✓ Обработка запущена")
    print("   Ожидание завершения...", end='', flush=True)
    
    # Ждем завершения
    while (time.time() - start_time) < timeout:
        if completed_file.exists():
            print()
            return "completed"
        elif error_file.exists():
            print()
            return "error"
        
        time.sleep(1)
        print('.', end='', flush=True)
    
    print()
    return "timeout"


def load_forms_from_file(file_path: Path) -> List[str]:
    """
    Загружает список форм из файла
    
    Args:
        file_path: Путь к файлу со списком форм
        
    Returns:
        List[str]: Список форм
    """
    forms = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Пропускаем пустые строки и комментарии
            if line and not line.startswith('#'):
                forms.append(line)
    return forms


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Form Context Collector - Agent Mode CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Собрать контекст для одной формы
  python form_context_cli.py agent --infobase "File=C:/Bases/Test/" \\
      --forms "Документ.ЗаказПокупателя.Форма.ФормаДокумента"

  # Собрать для нескольких форм
  python form_context_cli.py agent --infobase "File=C:/Bases/Test/" \\
      --forms "Документ.ЗаказПокупателя" "Справочник.Контрагенты"

  # Из файла со списком форм
  python form_context_cli.py agent --infobase "File=C:/Bases/Test/" \\
      --forms-file forms.txt --wait

  # Без закрытия 1С после завершения
  python form_context_cli.py agent --infobase "File=C:/Bases/Test/" \\
      --forms "Документ.ЗаказПокупателя" --no-close
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    # Команда agent
    agent_parser = subparsers.add_parser('agent', help='Запуск агентского режима')
    
    agent_parser.add_argument(
        '--infobase',
        required=True,
        help='Строка подключения к базе (File=C:/Bases/Test/)'
    )
    agent_parser.add_argument(
        '--forms',
        nargs='+',
        help='Список форм для сбора (Документ.ЗаказПокупателя.Форма.ФормаДокумента)'
    )
    agent_parser.add_argument(
        '--forms-file',
        type=Path,
        help='Файл со списком форм (по одной в строке)'
    )
    agent_parser.add_argument(
        '--include-invisible',
        action='store_true',
        help='Включать невидимые элементы'
    )
    agent_parser.add_argument(
        '--no-markdown',
        action='store_true',
        help='Не генерировать Markdown'
    )
    agent_parser.add_argument(
        '--no-close',
        action='store_true',
        help='Не закрывать 1С после завершения'
    )
    agent_parser.add_argument(
        '--wait',
        action='store_true',
        help='Ждать завершения обработки'
    )
    agent_parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Таймаут ожидания в секундах (по умолчанию: 300)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'agent':
        return run_agent_mode(args)
    
    return 0


def run_agent_mode(args) -> int:
    """
    Выполняет агентский режим
    
    Args:
        args: Аргументы командной строки
        
    Returns:
        int: Код возврата (0 = успех)
    """
    print("=" * 60)
    print("Form Context Collector - Agent Mode")
    print("=" * 60)
    
    # Собираем список форм
    forms = []
    
    if args.forms:
        for form in args.forms:
            forms.append({
                "type": "form_path",
                "value": form
            })
    
    if args.forms_file:
        if not args.forms_file.exists():
            print(f"❌ ОШИБКА: Файл не найден: {args.forms_file}", file=sys.stderr)
            return 1
        
        file_forms = load_forms_from_file(args.forms_file)
        for form in file_forms:
            forms.append({
                "type": "form_path",
                "value": form
            })
    
    if not forms:
        print("❌ ОШИБКА: Не указаны формы для обработки", file=sys.stderr)
        print("   Используйте --forms или --forms-file", file=sys.stderr)
        return 1
    
    print(f"\n📋 Форм для обработки: {len(forms)}")
    for i, form in enumerate(forms, 1):
        print(f"   {i}. {form['value']}")
    
    # Параметры обработки
    options = {
        "include_invisible": args.include_invisible,
        "generate_markdown": not args.no_markdown,
        "max_depth": 5,
        "close_after_collection": not args.no_close,
        "wait_form_timeout": 2000
    }
    
    print(f"\n⚙️  Настройки:")
    print(f"   Включать невидимые: {options['include_invisible']}")
    print(f"   Генерировать Markdown: {options['generate_markdown']}")
    print(f"   Закрывать 1С: {options['close_after_collection']}")
    
    # Создаем task.json
    script_dir = Path(__file__).parent
    task_file = create_task_file(forms, options)
    
    # Запускаем 1С
    processing_path = script_dir / "FormContextCollector.epf"
    
    if not processing_path.exists():
        print(f"\n❌ ОШИБКА: Обработка не найдена: {processing_path}", file=sys.stderr)
        print("   Убедитесь, что FormContextCollector.epf находится в каталоге с CLI", file=sys.stderr)
        return 1
    
    success = launch_1c(args.infobase, processing_path, wait=False)
    
    if not success:
        print("\n❌ Ошибка при запуске 1С", file=sys.stderr)
        return 1
    
    # Ждем завершения если требуется
    if args.wait:
        status = wait_for_completion(task_file, timeout=args.timeout)
        
        print("\n" + "=" * 60)
        if status == "completed":
            print("✅ Обработка завершена успешно")
            print("   Результаты сохранены в context/forms/")
            return 0
        elif status == "error":
            print("❌ Ошибка при обработке")
            print("   Проверьте лог: tools/form-context/debug.log")
            return 1
        else:
            print("⚠️  Превышен таймаут ожидания")
            print("   Обработка может продолжать работу в фоне")
            return 2
    else:
        print("\n✅ 1С запущен в фоновом режиме")
        print("   Проверьте статус: task.json.processing → task.json.completed")
        return 0


if __name__ == "__main__":
    sys.exit(main())