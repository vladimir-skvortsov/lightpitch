from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CommissionMood(str, Enum):
    """Настроение комиссии при задавании вопросов"""

    FRIENDLY = 'friendly'  # Доброжелательная
    NEUTRAL = 'neutral'  # Нейтральная
    STRICT = 'strict'  # Строгая
    SKEPTICAL = 'skeptical'  # Скептическая / Провокационная
    PRACTICAL = 'practical'  # Практико-ориентированная


class Question(BaseModel):
    """Модель вопроса"""

    id: str
    text: str
    category: str
    difficulty: str  # easy, medium, hard
    mood_characteristics: List[str]  # Характеристики настроения для этого вопроса
    follow_up_suggestions: Optional[List[str]] = None  # Дополнительные рекомендации


class QuestionGenerationRequest(BaseModel):
    """Запрос на генерацию вопросов"""

    text: str = Field(..., min_length=1, max_length=50000, description='Текст для генерации вопросов')
    commission_mood: CommissionMood = Field(..., description='Настроение комиссии')
    language: str = Field('ru', description='Язык вопросов')
    question_count: int = Field(10, ge=1, le=50, description='Количество вопросов для генерации')
    include_categories: Optional[List[str]] = Field(None, description='Включить только определенные категории')
    exclude_categories: Optional[List[str]] = Field(None, description='Исключить определенные категории')


class QuestionGenerationResponse(BaseModel):
    """Ответ с сгенерированными вопросами"""

    request_id: str
    questions: List[Question]
    total_questions: int
    categories: List[str]
    mood_description: str
    processing_time_seconds: float
    timestamp: datetime


@dataclass
class MoodCharacteristics:
    """Характеристики настроения комиссии"""

    name: str
    description: str
    question_style: str
    focus_areas: List[str]
    typical_questions: List[str]
    follow_up_style: str


# Конфигурация настроений комиссии
COMMISSION_MOODS = {
    CommissionMood.FRIENDLY: MoodCharacteristics(
        name='Доброжелательная',
        description='Задает уточняющие вопросы. Старается помочь раскрыть тему. Интересуется деталями, но мягко.',
        question_style='Уточняющие, поддерживающие, помогающие раскрыть тему',
        focus_areas=['Детализация', 'Углубление', 'Помощь в раскрытии', 'Интерес к работе'],
        typical_questions=[
            'Подготовьте подробные примеры и детали для каждого раздела работы',
            'Изучите логику ваших выводов и подготовьте пошаговое объяснение',
            'Продумайте, что можно добавить к каждому разделу для полноты картины',
            'Подготовьте рассказ о самых интересных моментах исследования',
        ],
        follow_up_style='Мягкие уточнения, поощрение, помощь в формулировках',
    ),
    CommissionMood.NEUTRAL: MoodCharacteristics(
        name='Нейтральная',
        description='Формальные вопросы по теме. Проверяет базовое понимание и соответствие работы стандартам.',
        question_style='Формальные, стандартные, проверочные',
        focus_areas=['Соответствие стандартам', 'Базовое понимание', 'Методология', 'Результаты'],
        typical_questions=[
            'Подготовьте четкое описание использованных методов с обоснованием выбора',
            'Изучите стандарты в вашей области и подготовьте сравнение с вашей работой',
            'Подготовьте структурированное изложение основных результатов',
            'Изучите методы оценки достоверности и подготовьте анализ ваших данных',
        ],
        follow_up_style='Стандартные уточнения, проверка понимания',
    ),
    CommissionMood.STRICT: MoodCharacteristics(
        name='Строгая',
        description='Акцент на слабые места работы. Могут придираться к формулировкам, источникам, методологии.',
        question_style='Критичные, придирчивые, проверяющие на прочность',
        focus_areas=['Слабые места', 'Методологические ошибки', 'Неточности', 'Недостатки'],
        typical_questions=[
            'Тщательно проанализируйте методологию и подготовьте обоснование каждого выбора',
            'Проверьте все утверждения и подготовьте ссылки на источники и доказательства',
            'Перечитайте все формулировки и подготовьте исправления неточностей',
            'Изучите альтернативные подходы и подготовьте обоснование их неприменимости',
        ],
        follow_up_style='Жесткие уточнения, требование обоснований, критика',
    ),
    CommissionMood.SKEPTICAL: MoodCharacteristics(
        name='Скептическая / Провокационная',
        description='Задает каверзные вопросы. Проверяет умение защищать позицию. Может сознательно провоцировать.',
        question_style='Провокационные, каверзные, проверяющие уверенность',
        focus_areas=['Спорные моменты', 'Альтернативные интерпретации', 'Критический анализ', 'Защита позиции'],
        typical_questions=[
            'Подготовьте обоснование правильности выбранного метода и альтернативные сценарии',
            'Изучите все возможные подходы и подготовьте сравнение с вашим выбором',
            'Исследуйте общепринятые взгляды и подготовьте аргументы за вашу позицию',
            'Проанализируйте возможные ошибки и подготовьте план их устранения',
        ],
        follow_up_style='Провокационные уточнения, проверка на стрессоустойчивость',
    ),
    CommissionMood.PRACTICAL: MoodCharacteristics(
        name='Практико-ориентированная',
        description='Интересуется применимостью результатов. Задает вопросы о практической ценности работы.',
        question_style='Практические, прикладные, ориентированные на применение',
        focus_areas=['Применимость', 'Практическая ценность', 'Реализация', 'Улучшения'],
        typical_questions=[
            'Подготовьте конкретные примеры практического применения ваших результатов',
            'Изучите реальные проблемы и подготовьте план их решения с помощью вашей работы',
            'Проанализируйте требования для внедрения и подготовьте план изменений',
            'Исследуйте возможности улучшения и подготовьте предложения по развитию',
        ],
        follow_up_style='Практические уточнения, вопросы о внедрении',
    ),
}
