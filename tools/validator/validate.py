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
import os
from pathlib import Path
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher, get_close_matches

# Импортируем наши модули для семантического анализа
try:
    from step_parser import StepParser, ParsedStep
    from semantic_matcher import SemanticMatcher, SemanticMatch
    from metrics_logger import MetricsLogger
    SEMANTIC_ANALYSIS_AVAILABLE = True
except ImportError:
    SEMANTIC_ANALYSIS_AVAILABLE = False
    print("⚠️ Семантический анализ и логирование метрик недоступны. Модули не найдены.")

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Определяем путь к корню проекта
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_LIBRARY = PROJECT_ROOT / 'data' / 'library-full.json'
METRICS_FILE = PROJECT_ROOT / 'data' / 'metrics.jsonl'


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
    
    def __init__(self, library_path: str, enable_semantic: bool = False):
        self.steps = []
        self.steps_normalized = {}  # нормализованный шаг -> оригинальный шаг
        self.enable_semantic = enable_semantic and SEMANTIC_ANALYSIS_AVAILABLE
        
        # Инициализируем парсер и matcher если доступны
        if self.enable_semantic:
            self.parser = StepParser()
            self.matcher = SemanticMatcher()
        
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
        Нормализация шага для сравнения.
        Для многострочных шагов (с таблицами или docstring)
        анализируется только первая строка.
        Заменяет параметры на плейсхолдеры.
        """
        # Для многострочных шагов берем только первую строку с текстом
        first_line = step.split('\n')[0].strip()

        # Удаляем ключевые слова (Дано, Когда, Тогда, И, Также, Затем)
        step = re.sub(r'^(Дано|Когда|Тогда|И|Также|Затем|Но)\s+', '', first_line, flags=re.IGNORECASE)
        
        # Приводим к нижнему регистру для единообразного сравнения
        step = step.lower()

        # Убираем двоеточие в конце, характерное для шагов с таблицами
        if step.endswith(':'):
            step = step[:-1].strip()
        
        # Заменяем текст в двойных кавычках на плейсхолдер
        step = re.sub(r'"[^"]*"', '"{}"', step)
        
        # Заменяем текст в одинарных кавычках на плейсхолдер
        step = re.sub(r"'[^']*'", '"{}"', step)
        
        # Заменяем экранированные кавычки из JSON (\") на обычные
        step = step.replace('\\"', '"')
        
        # Заменяем переменные ($Имя$) на плейсхолдер
        step = re.sub(r'\$[^$]+\$', '${}$', step)
        
        # Заменяем числа на плейсхолдер
        step = re.sub(r'\b\d+\b', '#', step)
        
        # Убираем лишние пробелы
        step = re.sub(r'\s+', ' ', step)
        
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
    
    def find_step_with_semantic(self, step: str) -> Dict:
        """
        Расширенный поиск с семантическим анализом
        Возвращает детальную информацию для AI
        """
        normalized = self.normalize_step(step)
        
        # Точное совпадение
        if normalized in self.steps_normalized:
            return {
                'found': True,
                'exact_match': self.steps_normalized[normalized],
                'suggestions': []
            }
        
        # Ищем похожие шаги с семантическим анализом
        suggestions = []
        
        for norm_step, orig_step in self.steps_normalized.items():
            similarity = SequenceMatcher(None, normalized, norm_step).ratio()
            
            if similarity > 0.7:  # порог схожести 70%
                suggestion_data = {
                    'text': orig_step,
                    'similarity': round(similarity, 2)
                }
                
                # Добавляем семантический анализ если включен
                if self.enable_semantic:
                    try:
                        # Парсим оригинальный и предлагаемый шаги
                        orig_parsed = self.parser.parse(step)
                        sugg_parsed = self.parser.parse(orig_step)
                        
                        # Проводим семантическое сравнение
                        semantic_match = self.matcher.compare(step, orig_step)
                        
                        suggestion_data['parsed'] = {
                            'action': sugg_parsed.action,
                            'element_type': sugg_parsed.element_type,
                            'context': sugg_parsed.context,
                            'params': sugg_parsed.params
                        }
                        
                        suggestion_data['semantic_match'] = semantic_match.to_dict()
                        suggestion_data['confidence'] = self.matcher.get_confidence_level(
                            semantic_match.confidence
                        )
                        
                    except Exception as e:
                        # Если семантический анализ не удался, продолжаем без него
                        pass
                
                suggestions.append(suggestion_data)
        
        # Сортируем по схожести
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Возвращаем топ-5
        return {
            'found': False,
            'exact_match': '',
            'suggestions': suggestions[:5]
        }


class ScenarioValidator:
    """Валидатор сценариев Gherkin"""
    
    KEYWORDS = ['Дано', 'Когда', 'Тогда', 'И', 'Также', 'Затем', 'Но']
    REQUIRED_HEADERS = ['# encoding:', '# language:']
    
    def __init__(self, library: StepLibrary, debug: bool = False, ai_enhanced: bool = False, logger: 'MetricsLogger' = None):
        self.library = library
        self.debug = debug
        self.ai_enhanced = ai_enhanced
        self.logger = logger
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
                'severity': 'auto_fix',
                'message': 'Отсутствует строка с кодировкой',
                'suggestion': 'Добавьте в начало файла: # encoding: utf-8',
                'fix': 'add_encoding'
            })
        
        if '# language:' not in first_lines:
            self.errors.append({
                'line': 1,
                'type': 'header',
                'severity': 'auto_fix',
                'message': 'Отсутствует строка с языком',
                'suggestion': 'Добавьте в начало файла: # language: ru',
                'fix': 'add_language'
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
        """Проверка всех шагов, включая многострочные"""
        in_scenario = False
        current_step_lines = []
        current_step_start_line = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            is_keyword_line = any(stripped.startswith(kw) for kw in self.KEYWORDS)
            is_new_scenario = stripped.startswith(('Сценарий:', 'Контекст:', 'Функционал:'))
            is_comment = stripped.startswith('#')
            is_empty = not stripped

            # Если мы встречаем новый шаг или начало нового сценария,
            # и у нас есть накопленный предыдущий шаг, то валидируем его.
            if current_step_lines and (is_keyword_line or is_new_scenario):
                full_step = "\n".join(current_step_lines)
                self.stats['total_steps'] += 1
                self._validate_step(current_step_start_line, full_step)
                current_step_lines = []

            if is_new_scenario:
                in_scenario = not stripped.startswith('Функционал:')
                continue

            if not in_scenario or is_comment or is_empty:
                continue

            if is_keyword_line:
                # Начинаем новый шаг
                current_step_start_line = i
                current_step_lines = [stripped]
            elif current_step_lines and (stripped.startswith('|') or stripped.startswith('"""')):
                # Продолжаем многострочный шаг (таблица или docstring)
                current_step_lines.append(stripped)

        # Валидируем последний шаг в файле, если он есть
        if current_step_lines:
            full_step = "\n".join(current_step_lines)
            self.stats['total_steps'] += 1
            self._validate_step(current_step_start_line, full_step)
    
    def _validate_step(self, line_num: int, step: str):
        """Валидация конкретного шага"""
        # Используем расширенный поиск если включен AI-enhanced режим
        if self.ai_enhanced and self.library.enable_semantic:
            result = self.library.find_step_with_semantic(step)
            found = result['found']
            exact_match = result['exact_match']
            suggestions = result.get('suggestions', [])
        else:
            found, exact_match, similar = self.library.find_step(step)
            suggestions = [{'text': s} for s in similar]
        
        if found:
            self.stats['valid_steps'] += 1
            if self.debug:
                print(f"{Colors.BLUE}✓ Шаг на строке {line_num} найден:{Colors.END} {step.splitlines()[0]}")
                print(f"{Colors.GREEN}  ↳ Соответствие в библиотеке:{Colors.END} {exact_match.splitlines()[0]}")
        else:
            self.stats['invalid_steps'] += 1
            
            error_info = {
                'line': line_num,
                'type': 'step',
                'step': step,
                'message': 'Шаг не найден в библиотеке',
                'suggestion': ''
            }
            
            # Определяем severity на основе наличия рекомендаций и их качества
            if not suggestions:
                error_info['severity'] = 'critical'
            elif self.ai_enhanced and suggestions:
                # Проверяем наличие безопасных рекомендаций
                has_safe = any(
                    s.get('semantic_match', {}).get('is_safe', False)
                    for s in suggestions
                )
                error_info['severity'] = 'semantic_check_required' if has_safe else 'critical'
            else:
                error_info['severity'] = 'semantic_check_required'
            
            if suggestions:
                if self.ai_enhanced:
                    error_info['suggestions'] = suggestions
                else:
                    error_info['similar_steps'] = [s['text'] for s in suggestions]
                error_info['suggestion'] = f'Возможно, вы имели в виду один из этих шагов'
            else:
                error_info['suggestion'] = 'Проверьте правильность написания шага или используйте другой шаг из библиотеки'
            
            # Добавляем parsed информацию для оригинального шага если включен AI-enhanced
            if self.ai_enhanced and self.library.enable_semantic:
                try:
                    orig_parsed = self.library.parser.parse(step)
                    error_info['parsed'] = {
                        'action': orig_parsed.action,
                        'element_type': orig_parsed.element_type,
                        'context': orig_parsed.context,
                        'params': orig_parsed.params
                    }
                except:
                    pass
            
            self.errors.append(error_info)
            
            # Логируем событие, если логгер включен
            if self.logger:
                self.logger.log_event('step_not_found', error_info)
    
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
                error_info = {
                    'line': i,
                    'type': 'syntax',
                    'severity': 'auto_fix',
                    'message': 'Использованы одинарные кавычки вместо двойных',
                    'suggestion': 'Замените одинарные кавычки \' на двойные "',
                    'fix': 'replace_quotes'
                }
                self.errors.append(error_info)
                if self.logger:
                    self.logger.log_event('auto_fix_suggestion', error_info)


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


def print_compact_report(result: Dict):
    """Вывод отчета в компактном формате для экономии токенов."""
    errors = result.get('errors', [])
    warnings = result.get('warnings', [])

    if not errors and not warnings:
        print("OK")
        return

    print("---")
    print("report:")
    if errors:
        print("  errors:")
        for error in errors:
            line = error.get('line', 0)
            step = error.get('step', '')
            message = error.get('message', '')
            
            # Для ошибок шагов выводим несколько лучших вариантов
            if error['type'] == 'step' and error.get('similar_steps'):
                print(f"    - line: {line}")
                print(f"      step: \"{step}\"")
                print(f"      suggestions:")
                for suggestion in error['similar_steps'][:3]:
                    print(f"        - \"{suggestion}\"")
            else: # Для остальных ошибок - просто сообщение
                print(f"    - line: {line}")
                print(f"      step: \"{step}\"")
                print(f"      error: \"{message}\"")
                print(f"      fix: \"{error.get('suggestion', '')}\"")

    if warnings:
        print("  warnings:")
        for warning in warnings:
            line = warning.get('line', 0)
            message = warning.get('message', '')
            print(f"    - line: {line}")
            print(f"      warning: \"{message}\"")
            print(f"      fix: \"{warning.get('suggestion', '')}\"")
    print("---")


def print_ai_enhanced_report(result: Dict):
    """Вывод отчета в расширенном формате YAML для AI"""
    import yaml
    
    errors = result.get('errors', [])
    warnings = result.get('warnings', [])
    
    # Убираем лишние детали для чистоты YAML
    clean_errors = []
    for error in errors:
        # Копируем чтобы не изменять оригинал
        err_copy = error.copy()
        
        # Удаляем поля, которые не нужны в AI-отчете
        err_copy.pop('message', None)
        err_copy.pop('suggestion', None)
        err_copy.pop('similar_steps', None)
        
        # Оставляем только 'text' в suggestions если нет семантики
        if 'suggestions' in err_copy and err_copy['suggestions']:
            if 'semantic_match' not in err_copy['suggestions'][0]:
                err_copy['suggestions'] = [s['text'] for s in err_copy['suggestions']]
        
        clean_errors.append(err_copy)
        
    report = {
        'report': {
            'errors': clean_errors,
            'warnings': warnings,
            'stats': result.get('stats', {})
        }
    }
    
    # Используем yaml для красивого вывода
    # allow_unicode=True для поддержки кириллицы
    # sort_keys=False для сохранения порядка
    print("---")
    try:
        # Пытаемся использовать PyYAML если он установлен
        print(yaml.dump(report, allow_unicode=True, sort_keys=False, indent=2))
    except ImportError:
        # Если нет - используем json.dumps с отступами
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as e:
        # На случай других ошибок сериализации
        print(json.dumps(report, ensure_ascii=False, indent=2))
        
    print("---")


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
        default=str(DEFAULT_LIBRARY),
        help=f'Путь к файлу библиотеки шагов (по умолчанию: {DEFAULT_LIBRARY})'
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
    parser.add_argument(
        '--ai-enhanced',
        action='store_true',
        help='Вывод в расширенном YAML-формате для AI с семантическим анализом'
    )
    parser.add_argument(
        '--compact', '-c',
        action='store_true',
        help='Вывод в компактном формате (для экономии токенов)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Включает режим отладки с выводом каждого успешного шага'
    )
    parser.add_argument(
        '--log-metrics',
        action='store_true',
        help='Включает логирование метрик в data/metrics.jsonl'
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
    
    # Инициализируем логгер, если нужно
    logger = None
    if args.log_metrics and SEMANTIC_ANALYSIS_AVAILABLE:
        logger = MetricsLogger(METRICS_FILE)
        print(f"📝 Логирование метрик включено. Файл: {METRICS_FILE}")

    # Загружаем библиотеку с учетом семантического анализа
    library = StepLibrary(args.library, enable_semantic=args.ai_enhanced)
    
    # Валидируем сценарий
    validator = ScenarioValidator(library, debug=args.debug, ai_enhanced=args.ai_enhanced, logger=logger)
    result = validator.validate_file(args.scenario)
    
    if 'error' in result:
        print(f"{Colors.RED}✗ Ошибка: {result['error']}{Colors.END}")
        sys.exit(1)
    
    # Выводим отчет в нужном формате
    if args.ai_enhanced:
        print_ai_enhanced_report(result)
    elif args.compact:
        print_compact_report(result)
    elif args.ai_format:
        print_report(result, verbose=args.verbose)
        print_recommendations_for_ai(result)
    else:
        print_report(result, verbose=args.verbose)
    
    # Возвращаем код выхода
    sys.exit(0 if not result['errors'] else 1)


if __name__ == '__main__':
    main()
