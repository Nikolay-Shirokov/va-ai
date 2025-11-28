#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для сбора метрик и обратной связи
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class MetricsLogger:
    """Логгер для сбора метрик валидации"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        # Создаем директорию если ее нет
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(
        self,
        event_type: str,
        details: Dict,
        ai_decision: Optional[Dict] = None,
        user_feedback: Optional[Dict] = None
    ):
        """
        Логирование события валидации
        
        Args:
            event_type: Тип события (e.g., 'auto_fix', 'semantic_check', 'escalation')
            details: Детали ошибки из валидатора
            ai_decision: Решение, принятое AI (e.g., 'apply', 'reject')
            user_feedback: Обратная связь от пользователя
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'ai_decision': ai_decision or {},
            'user_feedback': user_feedback or {}
        }
        
        try:
            # Записываем в формате JSON Lines для удобства
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️ Не удалось записать метрику: {e}")
