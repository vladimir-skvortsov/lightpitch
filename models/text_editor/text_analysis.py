"""
Text Analysis Logic - LangGraph and OpenAI GPT integration
Provides comprehensive text analysis with style transformation capabilities
OPTIMIZED VERSION - Combined prompts for faster processing
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from openai import OpenAI
import os
from datetime import datetime
import asyncio
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from dataclasses import dataclass
import re
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is required")


class TextStyle(str, Enum):
    CASUAL = "casual"
    PROFESSIONAL = "professional"
    SCIENTIFIC = "scientific"


class AnalysisType(str, Enum):
    WEAK_SPOTS = "weak_spots"
    SPEECH_TIME = "speech_time"
    REMOVE_PARASITES = "remove_parasites"
    REMOVE_BUREAUCRACY = "remove_bureaucracy"
    REMOVE_PASSIVE = "remove_passive"
    STRUCTURE_BLOCKS = "structure_blocks"
    STYLE_TRANSFORM = "style_transform"


class WeakSpot(BaseModel):
    position: int
    length: Optional[int] = None  
    original_text: str
    issue_type: str
    explanation: Optional[str] = None  
    suggestion: str
    severity: str


class ProcessingStep(BaseModel):
    step_name: str
    input_text: str
    output_text: str
    changes_made: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Text to analyze")
    analysis_types: List[AnalysisType] = Field(..., description="Types of analysis to perform")
    style: Optional[TextStyle] = Field(None, description="Style for transformation")
    language: str = Field("ru", description="Language code (ru, en, etc.)")


class TextAnalysisResponse(BaseModel):
    request_id: str
    original_text: str
    final_edited_text: str
    processing_steps: List[ProcessingStep]
    analysis_summary: Dict[str, Any]
    processing_time_seconds: float
    timestamp: datetime


class TextRecommendationsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    language: str = Field("ru", description="Language code")


class TextRecommendationsResponse(BaseModel):
    request_id: str
    weak_spots: List[WeakSpot]
    global_recommendations: List[str]
    processing_time_seconds: float
    timestamp: datetime


@dataclass
class AnalysisState:
    original_text: str
    current_text: str
    analysis_types: List[AnalysisType]
    style: Optional[TextStyle]
    language: str
    processing_steps: List[ProcessingStep]
    weak_spots: List[WeakSpot]
    speech_time_minutes: Optional[float] = None
    final_speech_time_minutes: Optional[float] = None
    word_count: int = 0
    final_word_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class OpenAIService:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI()

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response, handling cases where model adds extra text"""
        # Remove code fences first
        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            if json_end != -1:
                return text[json_start:json_end].strip()

        if "```" in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            if json_end != -1:
                return text[json_start:json_end].strip()

        start_idx = text.find('{')
        if start_idx == -1:
            return text.strip()

        brace_count = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx:i + 1]

        return text.strip()

    async def analyze_text(self, prompt: str, text: str, expect_json: bool = False) -> str:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        if expect_json and "gpt-4" in self.model:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(3):
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    **kwargs
                )

                content = response.choices[0].message.content
                return self._extract_json(content) if expect_json else content

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(keyword in error_str for keyword in
                                   ["rate_limit", "429", "503", "timeout", "server_error"])

                if is_retryable and attempt < 2:  
                    wait_time = 2 * (attempt + 1)  
                    logger.warning(f"Retryable error, waiting {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f"OpenAI API error: {str(e)}")
                raise Exception(f"AI service error: {str(e)}")


openai_service = OpenAIService()

class TextAnalysisService:
    def __init__(self):
        self.openai_service = openai_service
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        return {
            "weak_spots": """
                Ты — эксперт-редактор текста. Язык входного текста: {{LANG}}.
                Твоя задача: найти слабые места в тексте и дать точные рекомендации по исправлению. 
                Важно: ищи все категории проблем, не останавливайся на первых найденных.

                КРИТЕРИИ СЕРЬЕЗНОСТИ:
                - HIGH (ошибки): орфографические ошибки, грубые нарушения грамматики, фактические ошибки.
                - MEDIUM (предупреждения): длинные или перегруженные предложения, логические провалы, ошибки пунктуации, тяжёлые штампы.
                - LOW (замечания): стилистические улучшения, замена слов-паразитов, упрощение формулировок.

                ТИПЫ ПРОБЛЕМ (issue_type):
                1. clarity — неясная формулировка, двусмысленность
                Пример: "этот вопрос как-то не так понятен" → "этот вопрос непонятен"
                2. redundancy — повторы, лишние слова
                Пример: "он повторил это снова" → "он повторил это"
                3. bureaucracy — канцелярит, штампы
                Пример: "в целях осуществления" → "чтобы"
                4. filler — слова-паразиты
                Пример: "ну, как бы, в общем" → (удалить)
                5. passive_overuse — избыточный пассивный залог
                Пример: "было проведено исследование" → "мы провели исследование"
                6. logic_gap — логический провал, отсутствует связка
                Пример: "Мы сделали продукт. Поэтому продажи выросли в 10 раз" (нет связи)
                7. tone_mismatch — тон не соответствует задаче/аудитории
                Пример: "Чуваки, это бомба!" в деловой презентации
                8. term_misuse — неверное или чрезмерно сложное использование терминов
                Пример: "алгоритм называется гистограмма" (ошибка)
                9. punctuation_error — ошибки пунктуации
                Пример: "Слишком много текста мало пауз отсутствует call-to-action" → нужны запятые/точки
                10. wordiness — чрезмерно длинные предложения
                    Пример: длинное предложение на 5–6 строк без пауз
                11. other — другие проблемы

                ФОРМАТ ВЫВОДА (строго JSON, без преамбулы и без ```):
                {
                "weak_spots": [
                    {
                    "position": number,
                    "length": number,
                    "original_text": "проблемный фрагмент",
                    "issue_type": "один из 11 типов",
                    "explanation": "почему это проблема",
                    "suggestion": "как исправить",
                    "severity": "low|medium|high"
                    }
                ],
                "global_recommendations": [
                    "конкретная рекомендация 1",
                    "конкретная рекомендация 2"
                ]
                }

                ОБЯЗАТЕЛЬНО:
                - Старайся находить не только слова-паразиты, но и все другие виды проблем.
                - Указывай конкретные фрагменты текста, а не общие замечания.
                - Если подходящих проблем нет, возвращай пустой массив.
                """
        }

    def _normalize_weak_spot(self, spot: Dict[str, Any]) -> Dict[str, Any]:
        pos = spot.get("position")
        if isinstance(pos, str):
            try:
                spot["position"] = int(float(pos))
            except ValueError:
                spot["position"] = 0
        elif isinstance(pos, float):
            spot["position"] = int(pos)
        elif not isinstance(pos, int):
            spot["position"] = 0
        
        spot.setdefault("length", None)
        spot.setdefault("explanation", None)
        
        return spot

    async def analyze_weak_spots(self, text: str, language: str) -> tuple[List[WeakSpot], List[str]]:
        """Analyze text for weak spots without modifying it"""
        prompt = self.prompts["weak_spots"].replace("{{LANG}}", language)
        response = await self.openai_service.analyze_text(prompt, text, expect_json=True)

        try:
            data = json.loads(response)
            raw_spots = data.get("weak_spots", [])
            weak_spots = [
                WeakSpot(**self._normalize_weak_spot(spot))
                for spot in raw_spots
            ]
            recommendations = data.get("global_recommendations", [])
            return weak_spots, recommendations
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Failed to parse weak spots response: {e}")
            return [], ["Не удалось обработать анализ слабых мест"]

    async def process_text_combined(self, text: str, analysis_types: List[AnalysisType],
                                  style: Optional[TextStyle], language: str) -> Dict[str, Any]:
        """Process text with combined prompt for multiple operations"""

        processing_params = []
        tasks = []

        if AnalysisType.REMOVE_PARASITES in analysis_types:
            processing_params.append("remove_parasites")
            tasks.append("- Удали слова-паразиты, сохранив естественность")

        if AnalysisType.REMOVE_BUREAUCRACY in analysis_types:
            processing_params.append("remove_bureaucracy")
            tasks.append("- Упрости канцелярские обороты и бюрократические выражения")

        if AnalysisType.REMOVE_PASSIVE in analysis_types:
            processing_params.append("remove_passive")
            tasks.append("- Замени пассивный залог на активный где возможно")

        if AnalysisType.STRUCTURE_BLOCKS in analysis_types:
            processing_params.append("structure_blocks")
            tasks.append("- Структурируй текст по смысловым блокам с заголовками")

        if AnalysisType.STYLE_TRANSFORM in analysis_types and style:
            processing_params.append("style_transform")
            style_descriptions = {
                TextStyle.CASUAL: "неформальный, разговорный",
                TextStyle.PROFESSIONAL: "профессиональный, деловой",
                TextStyle.SCIENTIFIC: "научный, академический"
            }
            tasks.append(f"- Преобразуй в {style_descriptions.get(style, 'указанный')} стиль")

        tasks.append("- Рассчитай время выступления для исходного и финального текста")

        processing_params_str = ", ".join(processing_params)
        target_style_str = style.value if style else "не изменять"
        tasks_str = "\n".join(tasks)

        prompt = self.prompts["combined_processing"].format(
            processing_params=processing_params_str,
            target_style=target_style_str,
            language=language,
            tasks=tasks_str
        )

        response = await self.openai_service.analyze_text(prompt, text, expect_json=True)

        try:
            data = json.loads(response)
            return data
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Failed to parse combined processing response: {e}")
            words = len(text.split())
            speech_time = words / 150
            return {
                "processed_text": text,
                "speech_time_original": speech_time,
                "word_count_original": words,
                "speech_time_final": speech_time,
                "word_count_final": words,
                "changes_summary": ["Обработка не удалась"],
                "processing_details": {
                    "parasites_removed": 0,
                    "bureaucracy_simplified": False,
                    "passive_voice_changed": False,
                    "structure_added": False,
                    "style_transformed": None
                }
            }

    async def get_formatted_analysis(self, text: str, language: str) -> Dict[str, Any]:
        """Получить анализ текста в формате для интерфейса"""
        weak_spots, recommendations = await self.analyze_weak_spots(text, language)
        
        # Преобразуем weak_spots в новый формат
        good_practices = []
        warnings = []
        errors = []
        
        # Категоризируем проблемы по типам и серьезности
        for spot in weak_spots:
            item = {
                'title': self._get_issue_title(spot.issue_type),
                'description': spot.suggestion,
                'category': self._get_category_name(spot.issue_type),
                'position': f'Позиция: {spot.position}'
            }
            
            # Определяем тип по серьезности и типу проблемы
            if spot.severity == 'high' or spot.issue_type in ['punctuation_error', 'term_misuse']:
                errors.append({
                    **item,
                    'severity': 'high' if spot.severity == 'high' else 'medium'
                })
            elif spot.severity == 'medium' or spot.issue_type in ['wordiness', 'passive_overuse', 'clarity']:
                warnings.append(item)
        
        # Добавляем положительные моменты на основе отсутствия проблем
        issue_types_found = {spot.issue_type for spot in weak_spots}
        self._add_good_practices(good_practices, issue_types_found, text)
        
        # Рассчитываем общий балл
        total_issues = len(errors) * 3 + len(warnings) * 1
        text_length = len(text.split())
        base_score = max(50, 95 - (total_issues * 100 / max(text_length, 50)))
        
        return {
            'overall_score': round(base_score),
            'good_practices': good_practices,
            'warnings': warnings,
            'errors': errors,
            'recommendations': recommendations[:7]  # Ограничиваем до 7 рекомендаций
        }

    def _score_by_issue_density(self, issues_count: int, words: int, weight: float = 1.0) -> float:
        """Оценка 0..1 по плотности проблем на 1000 слов: меньше проблем — выше оценка"""
        words_safe = max(1, words)
        density = (issues_count * 1000.0) / words_safe
        penalty = min(0.6, (density / 50.0) * weight)  # 50 проблем/1000 слов дают сильный штраф
        return max(0.4, 1.0 - penalty)

    def _build_group(self, name: str, value: float, diagnostics: list, metrics: list) -> Dict[str, Any]:
        return {
            'name': name,
            'value': round(value, 2),
            'metrics': metrics,
            'diagnostics': diagnostics,
        }

    async def get_legacy_interface(self, text: str, language: str) -> Dict[str, Any]:
        """Сформировать интерфейс в «группах» для фронтенда
        Группы: Орфография, Слова‑паразиты, Канцеляризмы, Пассивный залог, Структура
        Метрики: Кол-во слов, Время выступления (мин)
        """
        weak_spots, recommendations = await self.analyze_weak_spots(text, language)
        words = len(text.split())
        speech_time_min = round(words / 150.0, 2)

        # Индексы по типам проблем
        by_type: Dict[str, list] = {}
        for ws in weak_spots:
            by_type.setdefault(ws.issue_type, []).append(ws)

        def diag_from_spots(spots: list, ok_label: str) -> list:
            if not spots:
                return [{
                    'label': ok_label,
                    'status': 'good',
                    'comment': None,
                }]
            diags = []
            for s in spots[:10]:  # ограничим вывод
                diags.append({
                    'label': s.original_text[:50] + ('...' if len(s.original_text) > 50 else ''),
                    'status': 'error' if s.severity == 'high' else 'warning',
                    'sublabel': None,
                    'comment': s.suggestion or s.explanation,
                })
            return diags

        # 1) Орфография (пока используем пунктуацию как прокси)
        ortho_spots = by_type.get('punctuation_error', [])
        ortho_value = self._score_by_issue_density(len(ortho_spots), words, weight=1.0)
        ortho_metrics = [
            {'label': 'Ошибки пунктуации', 'value': len(ortho_spots)},
            {'label': 'Количество слов', 'value': words},
            {'label': 'Время речи (мин)', 'value': speech_time_min},
        ]
        ortho_group = self._build_group('Орфография и пунктуация', ortho_value, diag_from_spots(ortho_spots, 'Ошибок не обнаружено'), ortho_metrics)

        # 2) Слова‑паразиты
        filler_spots = by_type.get('filler', [])
        filler_value = self._score_by_issue_density(len(filler_spots), words, weight=1.2)
        filler_metrics = [
            {'label': 'Встречи слов‑паразитов', 'value': len(filler_spots)},
        ]
        filler_group = self._build_group('Слова‑паразиты', filler_value, diag_from_spots(filler_spots, 'Паразитов не обнаружено'), filler_metrics)

        # 3) Канцеляризмы
        bur_spots = by_type.get('bureaucracy', [])
        bur_value = self._score_by_issue_density(len(bur_spots), words, weight=1.1)
        bur_metrics = [
            {'label': 'Канцеляризмов', 'value': len(bur_spots)},
        ]
        bur_group = self._build_group('Канцеляризмы', bur_value, diag_from_spots(bur_spots, 'Канцеляризмов не обнаружено'), bur_metrics)

        # 4) Пассивный залог
        passive_spots = by_type.get('passive_overuse', [])
        passive_value = self._score_by_issue_density(len(passive_spots), words, weight=1.0)
        passive_metrics = [
            {'label': 'Случаи пассивного залога', 'value': len(passive_spots)},
        ]
        passive_group = self._build_group('Пассивный залог', passive_value, diag_from_spots(passive_spots, 'Нет избыточного пассивного залога'), passive_metrics)

        # 5) Структура (логические провалы)
        structure_spots = by_type.get('logic_gap', [])
        structure_value = self._score_by_issue_density(len(structure_spots), words, weight=1.3)
        structure_metrics = [
            {'label': 'Логические разрывы', 'value': len(structure_spots)},
        ]
        structure_group = self._build_group('Структура', structure_value, diag_from_spots(structure_spots, 'Логических разрывов не обнаружено'), structure_metrics)

        # Итог и рекомендации
        groups = [
            ortho_group,
            bur_group,
            filler_group,
            passive_group,
            structure_group,
        ]

        # Генерируем детальную обратную связь через нейросеть
        detailed_feedback = await self._generate_detailed_feedback(text, weak_spots, by_type, words, language)
        
        return {
            'groups': groups,
            'feedback': detailed_feedback.get('feedback', 'Анализ завершен'),
            'strengths': detailed_feedback.get('strengths', []),
            'areas_for_improvement': detailed_feedback.get('areas_for_improvement', []),
            'recommendations': detailed_feedback.get('recommendations', recommendations[:7]),
        }

    async def _generate_detailed_feedback(self, text: str, weak_spots: list, by_type: dict, words: int, language: str) -> dict:
        """Генерирует детальную обратную связь через нейросеть"""
        
        # Подготавливаем данные для анализа
        issues_summary = []
        for issue_type, spots in by_type.items():
            if spots:
                issues_summary.append(f"{issue_type}: {len(spots)} проблем")
        
        issues_text = ", ".join(issues_summary) if issues_summary else "проблем не найдено"
        
        # Создаем промпт для детального анализа
        feedback_prompt = f"""
        Ты — эксперт-редактор текста. Проанализируй текст и найденные проблемы, затем дай детальную обратную связь.
        
        ТЕКСТ ДЛЯ АНАЛИЗА:
        {text[:2000]}...
        
        НАЙДЕННЫЕ ПРОБЛЕМЫ: {issues_text}
        КОЛИЧЕСТВО СЛОВ: {words}
        
        ВЕРНИ СТРОГО валидный JSON в следующем формате:
        {{
            "feedback": "краткая общая оценка текста (1-2 предложения)",
            "strengths": [
                "конкретная сильная сторона 1",
                "конкретная сильная сторона 2",
                "конкретная сильная сторона 3"
            ],
            "areas_for_improvement": [
                "конкретная область для улучшения 1", 
                "конкретная область для улучшения 2",
                "конкретная область для улучшения 3"
            ],
            "recommendations": [
                "конкретная рекомендация 1",
                "конкретная рекомендация 2", 
                "конкретная рекомендация 3",
                "конкретная рекомендация 4",
                "конкретная рекомендация 5"
            ]
        }}
        
        ТРЕБОВАНИЯ:
        - Будь конкретным и практичным
        - Учитывай найденные проблемы
        - Давай 3-5 сильных сторон (если есть)
        - Давай 3-5 областей для улучшения
        - Давай 5-7 конкретных рекомендаций
        - Пиши на русском языке
        - Если проблем мало, подчеркни сильные стороны
        - Если проблем много, сфокусируйся на главных недостатках
        """
        
        try:
            response = await self.openai_service.analyze_text(feedback_prompt, text, expect_json=True)
            data = json.loads(response)
            
            # Валидируем и очищаем данные
            return {
                'feedback': data.get('feedback', 'Анализ завершен'),
                'strengths': [s for s in data.get('strengths', []) if s and s.strip()],
                'areas_for_improvement': [a for a in data.get('areas_for_improvement', []) if a and a.strip()],
                'recommendations': [r for r in data.get('recommendations', []) if r and r.strip()],
            }
            
        except Exception as e:
            logger.warning(f"Failed to generate detailed feedback: {e}")
            # Fallback к простой эвристике
            avg_value = sum(len(by_type.get(issue_type, [])) for issue_type in ['punctuation_error', 'bureaucracy', 'filler', 'passive_overuse', 'logic_gap']) / 5.0
            
            if avg_value < 1:
                return {
                    'feedback': 'Отличный текст! Качество изложения высокое.',
                    'strengths': ['Хорошая структура', 'Понятный язык', 'Отсутствие серьезных ошибок'],
                    'areas_for_improvement': [],
                    'recommendations': ['Продолжайте в том же духе', 'Регулярно проверяйте текст на ошибки']
                }
            else:
                return {
                    'feedback': 'Текст требует доработки. Есть возможности для улучшения.',
                    'strengths': ['Хорошая тематика', 'Информативность'],
                    'areas_for_improvement': ['Исправление найденных ошибок', 'Улучшение стиля'],
                    'recommendations': ['Внимательно проверьте пунктуацию', 'Упростите сложные предложения', 'Уберите лишние слова']
                }

    def _get_issue_title(self, issue_type: str) -> str:
        """Получить заголовок проблемы"""
        titles = {
            'clarity': 'Неясная формулировка',
            'redundancy': 'Избыточность текста',
            'bureaucracy': 'Канцелярские обороты',
            'filler': 'Слова-паразиты',
            'passive_overuse': 'Злоупотребление пассивным залогом',
            'logic_gap': 'Нарушение логики',
            'tone_mismatch': 'Несоответствие тона',
            'term_misuse': 'Сложная терминология',
            'punctuation_error': 'Ошибки пунктуации',
            'wordiness': 'Длинные предложения',
            'other': 'Другие проблемы'
        }
        return titles.get(issue_type, 'Проблема текста')

    def _get_category_name(self, issue_type: str) -> str:
        """Получить название категории"""
        categories = {
            'clarity': 'Понятность',
            'redundancy': 'Стиль',
            'bureaucracy': 'Стиль',
            'filler': 'Лексика',
            'passive_overuse': 'Грамматика',
            'logic_gap': 'Структура',
            'tone_mismatch': 'Стиль',
            'term_misuse': 'Понятность',
            'punctuation_error': 'Грамматика',
            'wordiness': 'Стиль',
            'other': 'Общее'
        }
        return categories.get(issue_type, 'Общее')

    def _add_good_practices(self, good_practices: list, issues_found: set, text: str):
        """Добавить положительные практики на основе анализа"""
        
        # Проверяем структуру
        if 'logic_gap' not in issues_found:
            good_practices.append({
                'title': 'Четкая структура выступления',
                'description': 'Выступление имеет логичную последовательность идей',
                'category': 'Структура'
            })
        
        # Проверяем ясность
        if 'clarity' not in issues_found:
            good_practices.append({
                'title': 'Понятная формулировка идей',
                'description': 'Основные мысли изложены четко и доступно',
                'category': 'Содержание'
            })
        
        # Проверяем краткость
        if 'wordiness' not in issues_found and 'redundancy' not in issues_found:
            good_practices.append({
                'title': 'Краткость изложения',
                'description': 'Информация представлена без лишних слов',
                'category': 'Стиль'
            })
        
        # Проверяем отсутствие паразитов
        if 'filler' not in issues_found:
            good_practices.append({
                'title': 'Чистая речь',
                'description': 'Отсутствуют слова-паразиты и лишние элементы',
                'category': 'Лексика'
            })
        
        # Проверяем призыв к действию (эвристически)
        if any(word in text.lower() for word in ['рекомендую', 'предлагаю', 'призываю', 'действие', 'решение']):
            good_practices.append({
                'title': 'Призыв к действию',
                'description': 'В выступлении есть четкие рекомендации',
                'category': 'Заключение'
            })
        
        # Проверяем использование примеров
        if any(word in text.lower() for word in ['например', 'пример', 'случай', 'ситуация']):
            good_practices.append({
                'title': 'Использование примеров',
                'description': 'Для иллюстрации используются конкретные примеры',
                'category': 'Содержание'
            })
        
        # Если нет серьезных проблем с тоном
        if 'tone_mismatch' not in issues_found:
            good_practices.append({
                'title': 'Подходящий тон',
                'description': 'Стиль изложения соответствует цели выступления',
                'category': 'Стиль'
            })
        
        # Проверяем активный залог
        if 'passive_overuse' not in issues_found:
            good_practices.append({
                'title': 'Активная форма изложения',
                'description': 'Преобладает активный залог, что делает речь динамичной',
                'category': 'Грамматика'
            })

    def get_fallback_analysis(self):
        """Резервный анализ в случае ошибки API"""
        return {
            'overall_score': 75,
            'good_practices': [
                {
                    'title': 'Четкая структура выступления',
                    'description': 'Выступление имеет логичное построение',
                    'category': 'Структура',
                },
                {
                    'title': 'Понятная формулировка',
                    'description': 'Основные идеи изложены доступно',
                    'category': 'Содержание',
                },
            ],
            'warnings': [
                {
                    'title': 'Требуется детальный анализ',
                    'description': 'Для полного анализа необходимо повторить запрос',
                    'category': 'Система',
                    'position': 'Весь текст',
                },
            ],
            'errors': [],
            'recommendations': [
                'Повторите анализ для получения детальных рекомендаций',
                'Проверьте длину текста - очень короткие или длинные тексты анализируются хуже',
            ],
        }



def create_analysis_workflow() -> StateGraph:
    workflow = StateGraph(AnalysisState)

    async def analyze_weak_spots_node(state: AnalysisState) -> AnalysisState:
        """Analyze weak spots in ORIGINAL text only"""
        if AnalysisType.WEAK_SPOTS in state.analysis_types:
            service = TextAnalysisService()
            weak_spots, recommendations = await service.analyze_weak_spots(state.original_text, state.language)
            state.weak_spots = weak_spots
            state.metadata["weak_spots_recommendations"] = recommendations
        return state

    async def combined_processing_node(state: AnalysisState) -> AnalysisState:
        """Process text with combined prompt for all transformations"""
        processing_types = [t for t in state.analysis_types if t != AnalysisType.WEAK_SPOTS]

        if processing_types:
            service = TextAnalysisService()
            result = await service.process_text_combined(
                state.original_text, processing_types, state.style, state.language
            )

            state.current_text = result.get("processed_text", state.original_text)
            state.speech_time_minutes = result.get("speech_time_original")
            state.word_count = result.get("word_count_original", 0)
            state.final_speech_time_minutes = result.get("speech_time_final")
            state.final_word_count = result.get("word_count_final", 0)

            changes = result.get("changes_summary", ["Комплексная обработка выполнена"])
            metadata = result.get("processing_details", {})

            step_name_parts = []
            if AnalysisType.REMOVE_PARASITES in processing_types:
                step_name_parts.append("Удаление паразитов")
            if AnalysisType.REMOVE_BUREAUCRACY in processing_types:
                step_name_parts.append("Упрощение канцелярита")
            if AnalysisType.REMOVE_PASSIVE in processing_types:
                step_name_parts.append("Исправление залога")
            if AnalysisType.STRUCTURE_BLOCKS in processing_types:
                step_name_parts.append("Структурирование")
            if AnalysisType.STYLE_TRANSFORM in processing_types:
                step_name_parts.append("Преобразование стиля")

            step_name = "Комплексная обработка: " + ", ".join(step_name_parts)

            state.processing_steps.append(ProcessingStep(
                step_name=step_name,
                input_text=state.original_text,
                output_text=state.current_text,
                changes_made=changes,
                metadata=metadata
            ))

        return state

    workflow.add_node("analyze_weak_spots", analyze_weak_spots_node)
    workflow.add_node("combined_processing", combined_processing_node)

    workflow.set_entry_point("analyze_weak_spots")

    workflow.add_edge("analyze_weak_spots", "combined_processing")
    workflow.add_edge("combined_processing", END)

    return workflow


analysis_workflow = create_analysis_workflow()
memory = MemorySaver()
app_graph = analysis_workflow.compile(checkpointer=memory)