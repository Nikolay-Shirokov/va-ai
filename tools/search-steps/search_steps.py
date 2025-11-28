#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инструмент умного поиска шагов Vanessa Automation

Позволяет быстро находить релевантные шаги из библиотеки (1569 шагов)
по ключевым словам без необходимости загружать всю библиотеку в контекст AI.

Использование:
    # Простой поиск
    python search_steps.py --query "нажать кнопку создать" --top 5
    
    # Batch search (несколько запросов)
    python search_steps.py --query "открыть" "закрыть" "таблица" --top 5

Версия: 1.0 (MVP + Batch Search)
"""

import json
import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Определяем пути
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_LIBRARY = PROJECT_ROOT / 'data' / 'library-full.json'


class StepsLibrary:
    """Библиотека шагов Vanessa Automation"""
    
    def __init__(self, library_path: str):
        """
        Инициализация библиотеки
        
        Args:
            library_path: Путь к файлу library-full.json
        """
        self.steps = []  # Список всех шагов с метаданными
        self.steps_normalized = {}  # нормализованный шаг -> полная информация
        self.load_library(library_path)
    
    def load_library(self, path: str):
        """
        Загрузка библиотеки шагов из JSON
        
        Args:
            path: Путь к файлу библиотеки
            
        Raises:
            FileNotFoundError: Если файл не найден
            json.JSONDecodeError: Если JSON некорректный
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # library-full.json - это массив объектов
            if not isinstance(data, list):
                raise ValueError("Некорректный формат библиотеки: ожидается массив")
            
            # Обрабатываем каждый шаг
            for item in data:
                step_text = item.get('ИмяШага', '')
                if not step_text:
                    continue
                
                # Извлекаем категорию из ПолныйТипШага
                full_type = item.get('ПолныйТипШага', '')
                parts = full_type.split('.', 1)
                category = parts[0] if parts else 'Прочее'
                subcategory = parts[1] if len(parts) > 1 else ''
                
                # Сохраняем полную информацию
                step_info = {
                    'step': step_text,
                    'category': category,
                    'subcategory': subcategory,
                    'description': item.get('ОписаниеШага', '')
                }
                
                self.steps.append(step_info)
                
                # Нормализуем для быстрого поиска
                normalized = self.normalize_step(step_text)
                self.steps_normalized[normalized] = step_info
            
            if not self.steps:
                raise ValueError("Библиотека пуста или некорректна")
                
        except FileNotFoundError:
            print(f"✗ Ошибка: Файл библиотеки не найден: {path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"✗ Ошибка: Некорректный JSON в файле: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"✗ Ошибка загрузки библиотеки: {e}", file=sys.stderr)
            sys.exit(1)
    
    @staticmethod
    def normalize_step(step: str) -> str:
        """
        Нормализация шага для сравнения.
        Реализация из tools/validator/validate.py (строки 108-147)
        
        Args:
            step: Текст шага
            
        Returns:
            Нормализованный текст шага
        """
        # Для многострочных шагов берем только первую строку
        first_line = step.split('\n')[0].strip()
        
        # Удаляем ключевые слова Gherkin
        step = re.sub(
            r'^(Дано|Когда|Тогда|И|Также|Затем|Но)\s+',
            '',
            first_line,
            flags=re.IGNORECASE
        )
        
        # Приводим к нижнему регистру
        step = step.lower()
        
        # Убираем двоеточие в конце
        if step.endswith(':'):
            step = step[:-1].strip()
        
        # Заменяем текст в двойных кавычках на плейсхолдер
        step = re.sub(r'"[^"]*"', '"{}"', step)
        
        # Заменяем текст в одинарных кавычках на плейсхолдер
        step = re.sub(r"'[^']*'", '"{}"', step)
        
        # Заменяем экранированные кавычки
        step = step.replace('\\"', '"')
        
        # Заменяем переменные ($Имя$) на плейсхолдер
        step = re.sub(r'\$[^$]+\$', '${}$', step)
        
        # Заменяем числа на плейсхолдер
        step = re.sub(r'\b\d+\b', '#', step)
        
        # Убираем лишние пробелы
        step = re.sub(r'\s+', ' ', step)
        
        return step.strip()


class StepsSearcher:
    """Поиск и ранжирование шагов"""
    
    def __init__(self, library: StepsLibrary):
        """
        Инициализация поисковика
        
        Args:
            library: Загруженная библиотека шагов
        """
        self.library = library
    
    def search(self, query: str, top_n: int = 10, category: str = None) -> List[Dict]:
        """
        Поиск шагов по запросу
        
        Args:
            query: Поисковый запрос
            top_n: Количество возвращаемых результатов
            category: Фильтр по категории (опционально)
            
        Returns:
            Список найденных шагов с релевантностью
        """
        # Нормализуем запрос
        normalized_query = self.library.normalize_step(query)
        
        # Ищем похожие шаги
        matches = []
        
        for norm_step, step_info in self.library.steps_normalized.items():
            # Применяем фильтр по категории если нужен
            if category and step_info['category'] != category:
                continue
            
            # Вычисляем схожесть
            ratio = SequenceMatcher(None, normalized_query, norm_step).ratio()
            
            # Порог схожести 0.3 (более мягкий чем в validator для поиска)
            if ratio > 0.3:
                result = {
                    'step': step_info['step'],
                    'category': step_info['category'],
                    'relevance': round(ratio, 2)
                }
                
                # Добавляем подкатегорию если есть
                if step_info['subcategory']:
                    result['subcategory'] = step_info['subcategory']
                
                matches.append(result)
        
        # Сортируем по релевантности (убывание)
        matches.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Возвращаем топ-N результатов
        return matches[:top_n]
    
    def batch_search(self, queries: List[str], top_n: int = 10, category: str = None) -> Dict:
        """
        Поиск по нескольким запросам (batch search)
        
        Args:
            queries: Список поисковых запросов
            top_n: Количество результатов на запрос
            category: Фильтр по категории (опционально)
            
        Returns:
            Dict с результатами для каждого запроса
        """
        results = {}
        
        for query in queries:
            results[query] = self.search(query, top_n, category)
        
        # Подсчитываем общее количество результатов
        total_results = sum(len(r) for r in results.values())
        
        return {
            'total_queries': len(queries),
            'total_results': total_results,
            'results': results
        }


def format_json_output(data: Dict) -> str:
    """
    Форматирование вывода в JSON
    
    Args:
        data: Данные для вывода
        
    Returns:
        Отформатированная JSON строка
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


def main():
    """Основная функция CLI"""
    parser = argparse.ArgumentParser(
        description='Поиск шагов в библиотеке Vanessa Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Простой поиск
  python search_steps.py --query "нажать кнопку создать" --top 5
  
  # Batch search (несколько запросов)
  python search_steps.py --query "открыть" "закрыть" "таблица" --top 5
  
  # С фильтром по категории
  python search_steps.py --query "таблица" --category UI --top 10
        """
    )
    
    parser.add_argument(
        '--query',
        nargs='+',
        required=True,
        help='Поисковые запросы (можно указать несколько для batch search)'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='Количество результатов на запрос (по умолчанию: 10)'
    )
    
    parser.add_argument(
        '--category',
        help='Фильтр по категории (например: UI, Переменные, Прочее)'
    )
    
    parser.add_argument(
        '--library',
        default=str(DEFAULT_LIBRARY),
        help=f'Путь к файлу библиотеки (по умолчанию: {DEFAULT_LIBRARY})'
    )
    
    args = parser.parse_args()
    
    # Загружаем библиотеку
    library = StepsLibrary(args.library)
    
    # Создаем поисковик
    searcher = StepsSearcher(library)
    
    # Выполняем поиск
    if len(args.query) == 1:
        # Одиночный запрос - упрощенный формат
        query = args.query[0]
        results = searcher.search(query, args.top, args.category)
        
        output = {
            'query': query,
            'found': len(results),
            'results': results
        }
    else:
        # Batch search - полный формат
        output = searcher.batch_search(args.query, args.top, args.category)
    
    # Выводим результат в JSON
    print(format_json_output(output))


if __name__ == '__main__':
    main()