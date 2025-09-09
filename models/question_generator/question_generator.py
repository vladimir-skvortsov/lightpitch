import json
import logging
import uuid
from datetime import datetime
from typing import List

from ..text_editor.openai_client import OpenAIService
from .types import (
    COMMISSION_MOODS,
    CommissionMood,
    Question,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Генератор вопросов для защиты работы"""
    
    def __init__(self):
        self.openai_service = OpenAIService()
    
    def _get_question_generation_prompt(self, request: QuestionGenerationRequest) -> str:
        """Создает промпт для генерации вопросов на основе настроения комиссии"""
        mood_config = COMMISSION_MOODS[request.commission_mood]
        
        prompt = f"""
Ты - эксперт по академическим защитам. Твоя задача - сгенерировать {request.question_count} вопросов для комиссии по защите работы.

НАСТРОЕНИЕ КОМИССИИ: {mood_config.name}
Описание: {mood_config.description}
Стиль вопросов: {mood_config.question_style}
Фокусные области: {', '.join(mood_config.focus_areas)}
Типичные вопросы: {', '.join(mood_config.typical_questions)}

ИНСТРУКЦИИ:
1. Сгенерируй {request.question_count} рекомендаций по подготовке к защите в стиле "{mood_config.name}" комиссии
2. Рекомендации должны быть разнообразными по темам и сложности
3. Каждая рекомендация должна соответствовать характеристикам настроения комиссии
4. Включи рекомендации разных категорий: business, technical, personal, strategy, finance, product, market, team
5. Сложность: 30% легких, 50% средних, 20% сложных рекомендаций
6. Язык: {request.language}

КАТЕГОРИИ РЕКОМЕНДАЦИЙ:
- business: подготовка к вопросам о бизнес-модели, монетизации, стратегии развития
- technical: подготовка к техническим вопросам, методам, технологиям
- personal: подготовка к личным вопросам, мотивации, команде
- strategy: подготовка к стратегическому планированию, долгосрочным целям
- finance: подготовка к финансовым вопросам, бюджету, инвестициям
- product: подготовка к вопросам о продукте, его особенностях, разработке
- market: подготовка к вопросам о рынке, конкурентах, целевой аудитории
- team: подготовка к вопросам о команде, ролях, компетенциях

ФОРМАТ ОТВЕТА (JSON):
{{
    "questions": [
        {{
            "id": "unique_id",
            "text": "Конкретная рекомендация по подготовке к защите",
            "category": "business|technical|personal|strategy|finance|product|market|team",
            "difficulty": "easy|medium|hard",
            "mood_characteristics": ["характеристика1", "характеристика2"],
            "follow_up_suggestions": ["дополнительная рекомендация 1", "дополнительная рекомендация 2"]
        }}
    ],
    "categories": ["список всех категорий"],
    "mood_description": "Краткое описание настроения комиссии"
}}

ТЕКСТ ДЛЯ АНАЛИЗА:
{request.text}
"""
        return prompt
    
    async def generate_questions(self, request: QuestionGenerationRequest) -> QuestionGenerationResponse:
        """Генерирует вопросы на основе текста и настроения комиссии"""
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        try:
            prompt = self._get_question_generation_prompt(request)
            response = await self.openai_service.analyze_text(prompt, request.text, expect_json=True)
            
            # Парсинг ответа
            data = json.loads(response)
            questions_data = data.get('questions', [])
            categories = data.get('categories', [])
            mood_description = data.get('mood_description', COMMISSION_MOODS[request.commission_mood].description)
            
            # Фильтрация по категориям если указано
            if request.include_categories:
                questions_data = [q for q in questions_data if q.get('category') in request.include_categories]
            
            if request.exclude_categories:
                questions_data = [q for q in questions_data if q.get('category') not in request.exclude_categories]
            
            # Ограничение количества вопросов
            questions_data = questions_data[:request.question_count]
            
            # Создание объектов Question
            questions = []
            for i, q_data in enumerate(questions_data):
                question = Question(
                    id=q_data.get('id', f"q_{i+1}"),
                    text=q_data.get('text', ''),
                    category=q_data.get('category', 'общие'),
                    difficulty=q_data.get('difficulty', 'medium'),
                    mood_characteristics=q_data.get('mood_characteristics', []),
                    follow_up_suggestions=q_data.get('follow_up_suggestions', [])
                )
                questions.append(question)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return QuestionGenerationResponse(
                request_id=request_id,
                questions=questions,
                total_questions=len(questions),
                categories=categories,
                mood_description=mood_description,
                processing_time_seconds=processing_time,
                timestamp=datetime.now()
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            # Возвращаем базовые вопросы в случае ошибки
            return self._get_fallback_questions(request, request_id, start_time)
        
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return self._get_fallback_questions(request, request_id, start_time)
    
    def _get_fallback_questions(self, request: QuestionGenerationRequest, request_id: str, start_time: datetime) -> QuestionGenerationResponse:
        """Возвращает базовые вопросы в случае ошибки"""
        mood_config = COMMISSION_MOODS[request.commission_mood]
        
        fallback_questions = [
            Question(
                id="fallback_1",
                text="Подготовьте подробное описание вашей работы с конкретными примерами и результатами",
                category="business",
                difficulty="medium",
                mood_characteristics=[mood_config.question_style],
                follow_up_suggestions=["Подготовьте визуальные материалы", "Продумайте структуру ответа"]
            ),
            Question(
                id="fallback_2", 
                text="Изучите методологию вашего исследования и подготовьте объяснение выбора методов",
                category="technical",
                difficulty="easy",
                mood_characteristics=[mood_config.question_style],
                follow_up_suggestions=["Подготовьте сравнительный анализ методов", "Изучите альтернативные подходы"]
            )
        ]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return QuestionGenerationResponse(
            request_id=request_id,
            questions=fallback_questions,
            total_questions=len(fallback_questions),
            categories=["business", "technical"],
            mood_description=mood_config.description,
            processing_time_seconds=processing_time,
            timestamp=datetime.now()
        )
    
    def get_available_moods(self) -> List[dict]:
        """Возвращает список доступных настроений комиссии"""
        return [
            {
                "value": mood.value,
                "name": config.name,
                "description": config.description,
                "question_style": config.question_style,
                "focus_areas": config.focus_areas,
                "typical_questions": config.typical_questions
            }
            for mood, config in COMMISSION_MOODS.items()
        ]
    
    def get_mood_characteristics(self, mood: CommissionMood) -> dict:
        """Возвращает характеристики конкретного настроения"""
        config = COMMISSION_MOODS[mood]
        return {
            "name": config.name,
            "description": config.description,
            "question_style": config.question_style,
            "focus_areas": config.focus_areas,
            "typical_questions": config.typical_questions,
            "follow_up_style": config.follow_up_style
        }
