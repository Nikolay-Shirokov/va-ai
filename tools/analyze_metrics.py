#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для анализа файла с метриками (metrics.jsonl)

Анализирует собранные данные и выводит статистику:
- Общее количество событий
- Распределение по типам событий
- Топ-5 самых частых ненайденных шагов
- Топ-5 шагов с самыми низкими показателями семантической уверенности
"""

import json
from pathlib import Path
from collections import Counter
import argparse
import sys

# Определяем путь к файлу метрик
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
METRICS_FILE = PROJECT_ROOT / 'data' / 'metrics.jsonl'

class Colors:
    """ANSI цвета для терминала"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def analyze_metrics(log_file: Path):
    """
    Анализ файла метрик и вывод статистики
    """
    if not log_file.exists():
        print(f"{Colors.RED}✗ Файл с метриками не найден: {log_file}{Colors.END}")
        return

    events = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                events.append(json.loads(line))
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}✗ Ошибка чтения файла метрик: {e}{Colors.END}")
        return
    except Exception as e:
        print(f"{Colors.RED}✗ Не удалось прочитать файл: {e}{Colors.END}")
        return

    if not events:
        print(f"{Colors.YELLOW}Файл с метриками пуст. Нет данных для анализа.{Colors.END}")
        return

    print("\n" + "="*80)
    print(f"{Colors.BOLD}АНАЛИЗ МЕТРИК ВАЛИДАЦИИ ({len(events)} событий){Colors.END}")
    print("="*80 + "\n")

    # 1. Распределение по типам событий
    event_types = Counter(e['event_type'] for e in events)
    print(f"{Colors.BOLD}1. Распределение по типам событий:{Colors.END}")
    for event_type, count in event_types.most_common():
        print(f"  - {event_type}: {count}")
    print()

    # 2. Топ-5 ненайденных шагов
    step_not_found_events = [e for e in events if e['event_type'] == 'step_not_found']
    if step_not_found_events:
        step_counter = Counter(e['details']['step'] for e in step_not_found_events)
        print(f"{Colors.BOLD}2. Топ-5 самых частых ненайденных шагов:{Colors.END}")
        for step, count in step_counter.most_common(5):
            print(f"  - ({count} раз) {step}")
        print()

    # 3. Топ-5 шагов с низкой семантической уверенностью
    low_confidence_steps = []
    for event in step_not_found_events:
        if 'suggestions' in event['details'] and event['details']['suggestions']:
            # Проверяем, есть ли семантическая информация
            if 'semantic_match' in event['details']['suggestions'][0]:
                # Берем лучшую рекомендацию (первую)
                best_suggestion = event['details']['suggestions'][0]
                confidence = best_suggestion.get('semantic_match', {}).get('confidence', 1.0)
                if confidence < 0.8:
                     low_confidence_steps.append({
                         'step': event['details']['step'],
                         'suggestion': best_suggestion['text'],
                         'confidence': confidence
                     })

    if low_confidence_steps:
        # Сортируем по уверенности
        low_confidence_steps.sort(key=lambda x: x['confidence'])
        print(f"{Colors.BOLD}3. Примеры шагов, требующих внимания (низкая семантическая уверенность):{Colors.END}")
        for item in low_confidence_steps[:5]:
            print(f"  - Шаг: {item['step']}")
            print(f"    {Colors.YELLOW}↳ Лучшая рекомендация (уверенность: {item['confidence']}):{Colors.END} {item['suggestion']}")
    
    print("\n" + "="*80)
    print(f"{Colors.GREEN}Анализ завершен. Используйте эту информацию для улучшения правил и промптов.{Colors.END}")
    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Анализ метрик валидатора Vanessa Automation',
    )
    parser.add_argument(
        '--metrics-file',
        default=str(METRICS_FILE),
        help=f'Путь к файлу с метриками (по умолчанию: {METRICS_FILE})'
    )
    args = parser.parse_args()
    
    analyze_metrics(Path(args.metrics_file))


if __name__ == '__main__':
    main()