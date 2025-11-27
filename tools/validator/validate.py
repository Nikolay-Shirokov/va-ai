#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для валидации сценариев Vanessa Automation

Проверяет:
1. Все ли шаги из сценария есть в библиотеке шагов
2. Корректность синтаксиса Gherkin
3. Наличие обязательных элементов
4. Правильность использования переменных

Использование:
    python validate_scenario.py scenario.feature
    python validate_scenario.py scenario.feature --library БиблиотекаШагов.json
"""

import json
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher, get_close_matches


class Colors:
    """ANSI цвета для терминала"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class StepLibrary:
    """Библиотека шагов Vanessa Automation"""
    
    def __init__(self, library_path: str):
        self.steps = []
        self.steps_normalized = {}  # нормализованный шаг -> оригинальный шаг
        self.load_library(library_path)
    
    def load_library(self, path: str):
        """Загрузка библиотеки шагов из JSON"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Поддержка обоих форматов
            if isinstance(data, list):
                # Формат БиблиотекаШагов.json
                self.steps = [step.get('ИмяШага', '') for step in data]
            elif isinstance(data, dict):
                # Формат vanessa_steps_ai_knowledge.json
                for category, steps in data.items():
                    for step in steps:
                        self.steps.append(step.get('шаг', ''))
            
            # Нормализуем шаги для сравнения
            for step in self.steps:
                normalized = self.normalize_step(step)
                self.steps_normalized[normalized] = step
            
            print(f"{Colors.GREEN}✓ Загружено {len(self.steps)} шагов из библиотеки{Colors.END}")
            
        except FileNotFoundError:
            print(f"{Colors.RED}✗ Файл библиотеки не найден: {path}{Colors.END}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"{Colors.RED}✗ Ошибка парсинга JSON: {e}{Colors.END}")
            sys.exit(1)
    
    @staticmethod
    def normalize_step(step: str) -> str:
        """
        Нормализация шага для сравнения
        Заменяет параметры на плейсхолдеры
        """
        # Удаляем ключевые слова (Дано, Когда, Тогда, И, Также, Затем)
        step = re.sub(r'^(Дано|Когда|Тогда|И|Также|Затем|Но)\s+', '', step.strip())
        
        # Заменяем текст в кавычках на плейсхолдер
        step = re.sub(r'"[^"]*"', '"{}"', step)
        
        # Заменяем переменные ($Имя$) на плейсхолдер
        step = re.sub(r'\$[^$]+\$', '${}$', step)
        
        # Заменяем числа на плейсхолдер
        step = re.sub(r'\b\d+\b', '#', step)
        
        return step.strip()
    
    def find_step(self, step: str) -> Tuple[bool, str, List[str]]:
        """
        Поиск шага в библиотеке
        Возвращает: (найден, точное_совпадение, похожие_шаги)
        """
        normalized = self.normalize_step(step)
        
        # Точное совпадение
        if normalized in self.steps_normalized:
            return True, self.steps_normalized[normalized], []
        
        # Ищем похожие шаги
        similar = []
        for norm_step, orig_step in self.steps_normalized.items():
            ratio = SequenceMatcher(None, normalized, norm_step).ratio()
            if ratio > 0.7:  # порог схожести 70%
                similar.append((orig_step, ratio))
        
        # Сортируем по убыванию схожести
        similar.sort(key=lambda x: x[1], reverse=True)
        similar_steps = [s[0] for s in similar[:5]]  # топ-5
        
        return False, "", similar_steps


class ScenarioValidator:
    """Валидатор сценариев Gherkin"""
    
    KEYWORDS = ['Дано', 'Когда', 'Тогда', 'И', 'Также', 'Затем', 'Но']
    REQUIRED_HEADERS = ['# encoding:', '# language:']
    
    def __init__(self, library: StepLibrary):
        self.library = library
        self.errors = []
        self.warnings = []
        self.stats = {
            'total_steps': 0,
            'valid_steps': 0,
            'invalid_steps': 0,
            'scenarios': 0,
            'features': 0
        }
    
    def validate_file(self, filepath: str) -> Dict:
        """Валидация всего файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except FileNotFoundError:
            return {'error': f'Файл не найден: {filepath}'}
        except UnicodeDecodeError:
            return {'error': 'Ошибка кодировки. Используйте UTF-8.'}
        
        # Проверяем заголовки
        self._check_headers(lines)
        
        # Проверяем блок Функционал
        self._check_feature_block(lines)
        
        # Проверяем шаги
        self._check_steps(lines)
        
        # Проверяем переменные
        self._check_variables(lines)
        
        # Проверяем синтаксис кавычек
        self._check_quotes(lines)
        
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': self.stats
        }
    
    def _check_headers(self, lines: List[str]):
        """Проверка обязательных заголовков"""
        first_lines = '\n'.join(lines[:5])
        
        if '# encoding:' not in first_lines and '# -*- coding:' not in first_lines:
            self.errors.append({
                'line': 1,
                'type': 'header',
                'message': 'Отсутствует строка с кодировкой',
                'suggestion': 'Добавьте в начало файла: # encoding: utf-8'
            })
        
        if '# language:' not in first_lines:
            self.errors.append({
                'line': 1,
                'type': 'header',
                'message': 'Отсутствует строка с языком',
                'suggestion': 'Добавьте в начало файла: # language: ru'
            })
    
    def _check_feature_block(self, lines: List[str]):
        """Проверка блока Функционал"""
        has_feature = False
        
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('Функционал:'):
                has_feature = True
                self.stats['features'] += 1
                
                # Проверяем, есть ли описание
                if len(line.strip()) <= len('Функционал:') + 1:
                    self.warnings.append({
                        'line': i,
                        'type': 'feature',
                        'message': 'Функционал без названия',
                        'suggestion': 'Добавьте название после "Функционал:"'
                    })
            
            if line.strip().startswith('Сценарий:'):
                self.stats['scenarios'] += 1
        
        if not has_feature:
            self.errors.append({
                'line': 0,
                'type': 'structure',
                'message': 'Отсутствует блок "Функционал:"',
                'suggestion': 'Добавьте блок "Функционал:" перед сценариями'
            })
    
    def _check_steps(self, lines: List[str]):
        """Проверка всех шагов"""
        in_scenario = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Начало сценария
            if stripped.startswith(('Сценарий:', 'Контекст:')):
                in_scenario = True
                continue
            
            # Конец сценария (пустая строка или новый блок)
            if in_scenario and (not stripped or stripped.startswith(('Функционал:', 'Сценарий:'))):
                in_scenario = False
                continue
            
            # Проверяем шаги
            if in_scenario and any(stripped.startswith(kw) for kw in self.KEYWORDS):
                self.stats['total_steps'] += 1
                self._validate_step(i, stripped)
    
    def _validate_step(self, line_num: int, step: str):
        """Валидация конкретного шага"""
        found, exact_match, similar = self.library.find_step(step)
        
        if found:
            self.stats['valid_steps'] += 1
        else:
            self.stats['invalid_steps'] += 1
            
            error_info = {
                'line': line_num,
                'type': 'step',
                'step': step,
                'message': 'Шаг не найден в библиотеке',
                'suggestion': ''
            }
            
            if similar:
                error_info['similar_steps'] = similar
                error_info['suggestion'] = f'Возможно, вы имели в виду один из этих шагов'
            else:
                error_info['suggestion'] = 'Проверьте правильность написания шага или используйте другой шаг из библиотеки'
            
            self.errors.append(error_info)
    
    def _check_variables(self, lines: List[str]):
        """Проверка правильности использования переменных"""
        used_vars = set()
        defined_vars = set()
        
        for i, line in enumerate(lines, 1):
            # Ищем использование переменных ($ИмяПеременной$)
            used = re.findall(r'\$([^$]+)\$', line)
            for var in used:
                used_vars.add((var, i))
            
            # Ищем определение переменных (запоминаю ... в переменную)
            if 'в переменную' in line or 'как' in line:
                defined = re.findall(r'переменную "([^"]+)"', line)
                defined += re.findall(r'как "([^"]+)"', line)
                for var in defined:
                    defined_vars.add(var)
        
        # Проверяем неопределенные переменные
        for var, line_num in used_vars:
            if var not in defined_vars:
                self.warnings.append({
                    'line': line_num,
                    'type': 'variable',
                    'message': f'Переменная "${var}$" используется, но не определена',
                    'suggestion': f'Добавьте шаг для определения переменной "{var}" перед её использованием'
                })
    
    def _check_quotes(self, lines: List[str]):
        """Проверка правильности кавычек"""
        for i, line in enumerate(lines, 1):
            # Проверяем одинарные кавычки
            if "'" in line and any(line.strip().startswith(kw) for kw in self.KEYWORDS):
                self.errors.append({
                    'line': i,
                    'type': 'syntax',
                    'message': 'Использованы одинарные кавычки вместо двойных',
                    'suggestion': 'Замените одинарные кавычки \' на двойные "'
                })


def print_report(result: Dict, verbose: bool = False):
    """Вывод отчета о валидации"""
    print("\n" + "="*80)
    print(f"{Colors.BOLD}ОТЧЕТ О ВАЛИДАЦИИ СЦЕНАРИЯ{Colors.END}")
    print("="*80 + "\n")
    
    # Статистика
    stats = result['stats']
    print(f"{Colors.BOLD}📊 СТАТИСТИКА:{Colors.END}")
    print(f"  Функционалов: {stats['features']}")
    print(f"  Сценариев: {stats['scenarios']}")
    print(f"  Всего шагов: {stats['total_steps']}")
    print(f"  {Colors.GREEN}✓ Валидных шагов: {stats['valid_steps']}{Colors.END}")
    print(f"  {Colors.RED}✗ Невалидных шагов: {stats['invalid_steps']}{Colors.END}")
    
    # Прогресс-бар
    if stats['total_steps'] > 0:
        percent = (stats['valid_steps'] / stats['total_steps']) * 100
        bar_length = 40
        filled = int(bar_length * percent / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        color = Colors.GREEN if percent >= 90 else Colors.YELLOW if percent >= 70 else Colors.RED
        print(f"\n  {color}[{bar}] {percent:.1f}%{Colors.END}\n")
    
    # Ошибки
    errors = result['errors']
    if errors:
        print(f"{Colors.BOLD}{Colors.RED}❌ ОШИБКИ ({len(errors)}):{Colors.END}\n")
        
        for i, error in enumerate(errors, 1):
            print(f"{Colors.BOLD}{i}. Строка {error['line']}: {error['message']}{Colors.END}")
            
            if error['type'] == 'step' and verbose:
                print(f"   {Colors.CYAN}Шаг: {error['step']}{Colors.END}")
            
            print(f"   {Colors.YELLOW}💡 Рекомендация: {error['suggestion']}{Colors.END}")
            
            if 'similar_steps' in error and error['similar_steps']:
                print(f"   {Colors.MAGENTA}Похожие шаги из библиотеки:{Colors.END}")
                for j, similar in enumerate(error['similar_steps'][:3], 1):
                    print(f"      {j}. {similar}")
            
            print()
    else:
        print(f"{Colors.GREEN}✓ Ошибок не найдено!{Colors.END}\n")
    
    # Предупреждения
    warnings = result['warnings']
    if warnings:
        print(f"{Colors.BOLD}{Colors.YELLOW}⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}):{Colors.END}\n")
        
        for i, warning in enumerate(warnings, 1):
            print(f"{Colors.BOLD}{i}. Строка {warning['line']}: {warning['message']}{Colors.END}")
            print(f"   {Colors.YELLOW}💡 Рекомендация: {warning['suggestion']}{Colors.END}\n")
    
    # Итоговый вердикт
    print("="*80)
    if not errors:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ СЦЕНАРИЙ ВАЛИДЕН И ГОТОВ К ЗАПУСКУ!{Colors.END}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ ОШИБОК{Colors.END}")
    print("="*80 + "\n")


def print_recommendations_for_ai(result: Dict):
    """Вывод рекомендаций в формате для AI-ассистента"""
    errors = result['errors']
    
    if not errors:
        print(f"\n{Colors.GREEN}Все шаги корректны! Сценарий можно использовать.{Colors.END}\n")
        return
    
    print(f"\n{Colors.BOLD}📋 РЕКОМЕНДАЦИИ ДЛЯ AI-АССИСТЕНТА:{Colors.END}\n")
    print("Обнаружены следующие проблемы, которые нужно исправить:\n")
    
    step_errors = [e for e in errors if e['type'] == 'step']
    
    if step_errors:
        print(f"{Colors.RED}Шаги, не найденные в библиотеке:{Colors.END}\n")
        
        for i, error in enumerate(step_errors, 1):
            print(f"{i}. Строка {error['line']}:")
            print(f"   ❌ Неверный шаг: {error['step']}")
            
            if 'similar_steps' in error and error['similar_steps']:
                print(f"   ✅ Замените на один из этих шагов:")
                for j, similar in enumerate(error['similar_steps'][:2], 1):
                    print(f"      {j}) {similar}")
            else:
                print(f"   ⚠️  Похожих шагов не найдено. Выберите другой подход из библиотеки.")
            print()
    
    other_errors = [e for e in errors if e['type'] != 'step']
    if other_errors:
        print(f"{Colors.YELLOW}Другие проблемы:{Colors.END}\n")
        for error in other_errors:
            print(f"• {error['message']} (строка {error['line']})")
            print(f"  Решение: {error['suggestion']}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Валидация сценариев Vanessa Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python validate_scenario.py scenario.feature
  python validate_scenario.py scenario.feature --library БиблиотекаШагов.json
  python validate_scenario.py scenario.feature --verbose --ai-format
        """
    )
    
    parser.add_argument('scenario', help='Путь к файлу сценария (.feature)')
    parser.add_argument(
        '--library', '-l',
        default='БиблиотекаШагов.json',
        help='Путь к файлу библиотеки шагов (по умолчанию: БиблиотекаШагов.json)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод'
    )
    parser.add_argument(
        '--ai-format',
        action='store_true',
        help='Вывод рекомендаций в формате для AI-ассистента'
    )
    
    args = parser.parse_args()
    
    # Проверяем существование файлов
    if not Path(args.scenario).exists():
        print(f"{Colors.RED}✗ Файл сценария не найден: {args.scenario}{Colors.END}")
        sys.exit(1)
    
    if not Path(args.library).exists():
        print(f"{Colors.RED}✗ Файл библиотеки не найден: {args.library}{Colors.END}")
        print(f"{Colors.YELLOW}Используйте --library для указания пути к БиблиотекаШагов.json{Colors.END}")
        sys.exit(1)
    
    print(f"\n{Colors.BOLD}Валидация сценария: {args.scenario}{Colors.END}")
    print(f"Библиотека шагов: {args.library}\n")
    
    # Загружаем библиотеку
    library = StepLibrary(args.library)
    
    # Валидируем сценарий
    validator = ScenarioValidator(library)
    result = validator.validate_file(args.scenario)
    
    if 'error' in result:
        print(f"{Colors.RED}✗ Ошибка: {result['error']}{Colors.END}")
        sys.exit(1)
    
    # Выводим отчет
    print_report(result, verbose=args.verbose)
    
    # Выводим рекомендации для AI
    if args.ai_format:
        print_recommendations_for_ai(result)
    
    # Возвращаем код выхода
    sys.exit(0 if not result['errors'] else 1)


if __name__ == '__main__':
    main()
