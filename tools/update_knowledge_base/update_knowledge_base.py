#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления базы знаний из новой библиотеки шагов Vanessa Automation

Использование:
    python update_knowledge_base.py БиблиотекаШагов.json
    python update_knowledge_base.py БиблиотекаШагов.json --output-dir ai-knowledge/
    python update_knowledge_base.py БиблиотекаШагов.json --dry-run
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any


class KnowledgeBaseUpdater:
    """Обновление базы знаний AI из библиотеки шагов Vanessa"""
    
    def __init__(self, source_file: str, output_dir: str = None, dry_run: bool = False):
        self.source_file = Path(source_file)
        self.output_dir = Path(output_dir) if output_dir else Path('ai-knowledge')
        self.data_dir = Path('data')
        self.dry_run = dry_run
        
        self.stats = {
            'total_steps': 0,
            'categories': 0,
            'subcategories': 0,
            'new_steps': 0,
            'updated_steps': 0,
            'removed_steps': 0
        }
        
        self.library_data = []
        self.old_knowledge = {}
    
    def log(self, message: str, level: str = 'INFO'):
        """Логирование"""
        prefix = {
            'INFO': '✓',
            'WARN': '⚠',
            'ERROR': '✗',
            'DRY': '🔍',
            'SUCCESS': '✅'
        }.get(level, '·')
        
        print(f"{prefix} {message}")
    
    def load_source_library(self):
        """Загрузка исходной библиотеки шагов"""
        if not self.source_file.exists():
            raise FileNotFoundError(f"Файл не найден: {self.source_file}")
        
        self.log(f"Загрузка библиотеки из {self.source_file}...")
        
        try:
            with open(self.source_file, 'r', encoding='utf-8') as f:
                self.library_data = json.load(f)
            
            self.stats['total_steps'] = len(self.library_data)
            self.log(f"Загружено {self.stats['total_steps']} шагов", 'SUCCESS')
            
        except json.JSONDecodeError as e:
            raise Exception(f"Ошибка парсинга JSON: {e}")
        except Exception as e:
            raise Exception(f"Ошибка чтения файла: {e}")
    
    def load_old_knowledge(self):
        """Загрузка старой базы знаний для сравнения"""
        old_file = self.output_dir / 'steps-library.json'
        
        if not old_file.exists():
            self.log("Старая база знаний не найдена (первое создание)", 'WARN')
            return
        
        try:
            with open(old_file, 'r', encoding='utf-8') as f:
                self.old_knowledge = json.load(f)
            
            old_count = sum(len(steps) for steps in self.old_knowledge.values())
            self.log(f"Загружена старая база: {old_count} шагов")
            
        except Exception as e:
            self.log(f"Не удалось загрузить старую базу: {e}", 'WARN')
    
    def create_ai_knowledge_base(self) -> Dict[str, List[Dict]]:
        """
        Создание оптимизированной базы знаний для AI
        Группировка по основным категориям
        """
        self.log("\nСоздание базы знаний для AI...")
        
        knowledge_base = defaultdict(list)
        
        for step in self.library_data:
            step_type = step.get('ПолныйТипШага', 'Неизвестно')
            
            # Определяем основную категорию
            if '.' in step_type:
                main_category = step_type.split('.')[0]
            else:
                main_category = step_type
            
            # Добавляем шаг в категорию
            knowledge_base[main_category].append({
                "шаг": step.get('ИмяШага', ''),
                "описание": step.get('ОписаниеШага', ''),
                "тип": step_type
            })
        
        # Сортируем категории по количеству шагов
        sorted_kb = dict(sorted(
            knowledge_base.items(),
            key=lambda x: len(x[1]),
            reverse=True
        ))
        
        self.stats['categories'] = len(sorted_kb)
        
        # Подсчитываем подкатегории
        subcategories = set()
        for step in self.library_data:
            step_type = step.get('ПолныйТипШага', '')
            if '.' in step_type:
                subcategories.add(step_type)
        self.stats['subcategories'] = len(subcategories)
        
        return sorted_kb
    
    def compare_with_old(self, new_kb: Dict):
        """Сравнение с старой базой знаний"""
        if not self.old_knowledge:
            self.log("Нет старой базы для сравнения", 'WARN')
            return
        
        self.log("\nСравнение с предыдущей версией...")
        
        # Создаем множества шагов для сравнения
        old_steps = set()
        for category, steps in self.old_knowledge.items():
            for step in steps:
                old_steps.add(step['шаг'])
        
        new_steps = set()
        for category, steps in new_kb.items():
            for step in steps:
                new_steps.add(step['шаг'])
        
        # Находим изменения
        added = new_steps - old_steps
        removed = old_steps - new_steps
        
        self.stats['new_steps'] = len(added)
        self.stats['removed_steps'] = len(removed)
        
        if added:
            self.log(f"Новых шагов: {len(added)}", 'INFO')
            if len(added) <= 10:
                for step in list(added)[:10]:
                    self.log(f"  + {step[:80]}...", 'INFO')
        
        if removed:
            self.log(f"Удаленных шагов: {len(removed)}", 'WARN')
            if len(removed) <= 10:
                for step in list(removed)[:10]:
                    self.log(f"  - {step[:80]}...", 'WARN')
    
    def generate_statistics(self, knowledge_base: Dict) -> Dict:
        """Генерация статистики по библиотеке"""
        stats = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "total_steps": self.stats['total_steps'],
            "total_categories": self.stats['categories'],
            "total_subcategories": self.stats['subcategories'],
            "categories": {}
        }
        
        for category, steps in knowledge_base.items():
            # Подсчитываем подкатегории в этой категории
            subcats = set()
            for step in steps:
                step_type = step['тип']
                if '.' in step_type:
                    parts = step_type.split('.')
                    if len(parts) > 1:
                        subcats.add('.'.join(parts[1:]))
            
            stats["categories"][category] = {
                "steps_count": len(steps),
                "subcategories_count": len(subcats),
                "subcategories": sorted(list(subcats))
            }
        
        return stats
    
    def save_files(self, knowledge_base: Dict, statistics: Dict):
        """Сохранение всех файлов"""
        
        if self.dry_run:
            self.log("\n🔍 РЕЖИМ ПРЕДПРОСМОТРА - файлы НЕ будут сохранены", 'DRY')
            return
        
        self.log("\nСохранение файлов...")
        
        # Создаем директории
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Сохраняем оптимизированную базу знаний для AI
        ai_kb_file = self.output_dir / 'steps-library.json'
        with open(ai_kb_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
        
        size_kb = ai_kb_file.stat().st_size / 1024
        self.log(f"✓ {ai_kb_file} ({size_kb:.0f} KB)", 'SUCCESS')
        
        # 2. Копируем полную библиотеку в data/
        full_lib_file = self.data_dir / 'library-full.json'
        with open(full_lib_file, 'w', encoding='utf-8') as f:
            json.dump(self.library_data, f, ensure_ascii=False, indent=2)
        
        size_kb = full_lib_file.stat().st_size / 1024
        self.log(f"✓ {full_lib_file} ({size_kb:.0f} KB)", 'SUCCESS')
        
        # 3. Сохраняем статистику
        stats_file = self.data_dir / 'statistics.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2)
        
        self.log(f"✓ {stats_file}", 'SUCCESS')
        
        # 4. Создаем README для ai-knowledge
        self.create_ai_knowledge_readme(statistics)
        
        # 5. Обновляем README для data
        self.create_data_readme(statistics)
    
    def create_ai_knowledge_readme(self, stats: Dict):
        """Создание/обновление README для ai-knowledge"""
        readme_file = self.output_dir / 'README.md'
        
        content = f"""# База знаний для AI

## 📥 Что загрузить в AI

Загрузите эти **3 файла** в ваш AI-ассистент:

1. ✅ `guide.md` (27 KB) - Руководство для AI
2. ✅ `templates.md` (31 KB) - Шаблоны сценариев  
3. ✅ `steps-library.json` (655 KB) - База из {stats['total_steps']} шагов

**Итого:** ~715 KB

## 📊 Статистика библиотеки

**Обновлено:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

- **Всего шагов:** {stats['total_steps']}
- **Категорий:** {stats['total_categories']}
- **Подкатегорий:** {stats['total_subcategories']}

### Топ-10 категорий по количеству шагов

"""
        
        # Топ-10 категорий
        sorted_categories = sorted(
            stats['categories'].items(),
            key=lambda x: x[1]['steps_count'],
            reverse=True
        )
        
        for i, (category, cat_stats) in enumerate(sorted_categories[:10], 1):
            content += f"{i}. **{category}** - {cat_stats['steps_count']} шагов "
            content += f"({cat_stats['subcategories_count']} подкатегорий)\n"
        
        content += """
## 🤖 Совместимость

- ✅ Claude (Anthropic) - рекомендуется
- ✅ ChatGPT (OpenAI)
- ✅ Gemini (Google)
- ✅ Другие LLM

## 📖 Использование

1. Загрузите 3 файла в чат с AI
2. Используйте промпт из `/templates/prompts/`
3. Начинайте создавать сценарии!

[Подробная инструкция →](../docs/quick-start.md)

---

**Версия:** {stats['version']}  
**Обновлено:** {stats['updated_at'][:10]}
"""
        
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.log(f"✓ {readme_file}", 'SUCCESS')
    
    def create_data_readme(self, stats: Dict):
        """Создание/обновление README для data"""
        readme_file = self.data_dir / 'README.md'
        
        content = f"""# Дополнительные данные

## 📁 Содержимое

### library-full.json
Полная библиотека шагов из Vanessa Automation в оригинальном формате.

- **Размер:** ~680 KB
- **Формат:** JSON массив объектов
- **Шагов:** {stats['total_steps']}
- **Обновлено:** {datetime.now().strftime('%d.%m.%Y')}

### statistics.json
Детальная статистика по библиотеке шагов.

- Количество шагов по категориям
- Список подкатегорий
- Метаданные обновления

### steps-compact.md
Компактный справочник наиболее используемых шагов.

- **Размер:** ~55 KB
- **Формат:** Markdown
- Группировка по категориям
- Примеры использования

## 🔄 Обновление

Для обновления библиотеки из Vanessa Automation:

```bash
python tools/update_knowledge_base.py path/to/БиблиотекаШагов.json
```

## 📊 Текущая статистика

**Последнее обновление:** {stats['updated_at'][:10]}

- Всего шагов: {stats['total_steps']}
- Категорий: {stats['total_categories']}
- Подкатегорий: {stats['total_subcategories']}

### Категории

"""
        
        # Список всех категорий
        sorted_categories = sorted(
            stats['categories'].items(),
            key=lambda x: x[1]['steps_count'],
            reverse=True
        )
        
        for category, cat_stats in sorted_categories:
            content += f"- **{category}**: {cat_stats['steps_count']} шагов\n"
        
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.log(f"✓ {readme_file}", 'SUCCESS')
    
    def print_summary(self):
        """Вывод итоговой статистики"""
        self.log("\n" + "="*70)
        self.log("ИТОГОВАЯ СТАТИСТИКА")
        self.log("="*70 + "\n")
        
        mode = "РЕЖИМ ПРЕДПРОСМОТРА" if self.dry_run else "ОБНОВЛЕНИЕ ЗАВЕРШЕНО"
        self.log(f"Режим: {mode}\n")
        
        self.log(f"📊 Библиотека шагов:")
        self.log(f"   Всего шагов: {self.stats['total_steps']}")
        self.log(f"   Категорий: {self.stats['categories']}")
        self.log(f"   Подкатегорий: {self.stats['subcategories']}")
        
        if self.old_knowledge:
            self.log(f"\n🔄 Изменения:")
            self.log(f"   Новых шагов: {self.stats['new_steps']}", 
                    'INFO' if self.stats['new_steps'] else 'INFO')
            self.log(f"   Удаленных шагов: {self.stats['removed_steps']}", 
                    'WARN' if self.stats['removed_steps'] else 'INFO')
        
        if not self.dry_run:
            self.log(f"\n📁 Созданные файлы:")
            self.log(f"   {self.output_dir}/steps-library.json (для AI)")
            self.log(f"   {self.output_dir}/README.md")
            self.log(f"   {self.data_dir}/library-full.json")
            self.log(f"   {self.data_dir}/statistics.json")
            self.log(f"   {self.data_dir}/README.md")
        
        self.log("")
        
        if self.dry_run:
            self.log("Для применения изменений запустите без --dry-run", 'WARN')
        else:
            self.log("✅ База знаний успешно обновлена!", 'SUCCESS')
            self.log("\nСледующие шаги:")
            self.log("1. Проверьте обновленные файлы")
            self.log("2. Закоммитьте изменения в Git")
            self.log("3. Загрузите новые файлы в AI для тестирования")
        
        self.log("")
    
    def update(self):
        """Главная функция обновления"""
        try:
            self.log("="*70)
            self.log("ОБНОВЛЕНИЕ БАЗЫ ЗНАНИЙ VANESSA AUTOMATION")
            self.log("="*70 + "\n")
            
            if self.dry_run:
                self.log("⚠️  РЕЖИМ ПРЕДПРОСМОТРА", 'WARN')
                self.log("Изменения не будут применены\n")
            
            # Загружаем данные
            self.load_source_library()
            self.load_old_knowledge()
            
            # Создаем новую базу знаний
            knowledge_base = self.create_ai_knowledge_base()
            
            # Сравниваем с предыдущей версией
            self.compare_with_old(knowledge_base)
            
            # Генерируем статистику
            statistics = self.generate_statistics(knowledge_base)
            
            # Сохраняем файлы
            self.save_files(knowledge_base, statistics)
            
            # Итоговая статистика
            self.print_summary()
            
            return True
            
        except Exception as e:
            self.log(f"Ошибка: {e}", 'ERROR')
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Обновление базы знаний из библиотеки шагов Vanessa Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:

  # Обновление с дефолтными настройками
  python update_knowledge_base.py БиблиотекаШагов.json

  # Предпросмотр без изменений
  python update_knowledge_base.py БиблиотекаШагов.json --dry-run

  # Указание директории для ai-knowledge
  python update_knowledge_base.py БиблиотекаШагов.json --output-dir ai-knowledge/

  # Полный пример
  python update_knowledge_base.py /path/to/БиблиотекаШагов.json \\
      --output-dir ai-knowledge/ \\
      --dry-run

Файлы будут созданы:
  - ai-knowledge/steps-library.json (оптимизированная база для AI)
  - ai-knowledge/README.md (инструкция)
  - data/library-full.json (полная библиотека)
  - data/statistics.json (статистика)
  - data/README.md (описание данных)
        '''
    )
    
    parser.add_argument(
        'source',
        help='Путь к файлу БиблиотекаШагов.json'
    )
    
    parser.add_argument(
        '--output-dir',
        default='ai-knowledge',
        help='Директория для ai-knowledge (по умолчанию: ai-knowledge)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим предпросмотра без применения изменений'
    )
    
    args = parser.parse_args()
    
    # Создаем апдейтер и запускаем
    updater = KnowledgeBaseUpdater(
        source_file=args.source,
        output_dir=args.output_dir,
        dry_run=args.dry_run
    )
    
    success = updater.update()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
