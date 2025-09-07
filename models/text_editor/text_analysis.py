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
                Задача: выявить слабые места и предложить конкретные улучшения.
                
                ВАЖНО:
                - Верни СТРОГО валидный JSON без преамбулы и без кодовых блоков.
                - Используй ТОЛЬКО issue_type из списка ниже (один на элемент):
                  1. clarity — неясная формулировка, двусмысленность
                  2. redundancy — повторы, лишние слова
                  3. bureaucracy — канцелярит, тяжёлые штампы
                  4. filler — слова-паразиты
                  5. passive_overuse — избыточный пассивный залог
                  6. logic_gap — логический провал, нет связки/обоснования
                  7. tone_mismatch — тон не соответствует задаче/аудитории
                  8. term_misuse — неверное использование терминов/жаргона
                  9. punctuation_error — ошибки пунктуации
                  10. wordiness — чрезмерно длинные и тяжёлые предложения
                  11. other - если проблема не попадает в список.
                
                ФОРМАТ ВЫВОДА:
                {
                  "position_mode": "chars",
                  "weak_spots": [
                    {
                      "position": number,            // индекс начала фрагмента
                      "length": number,              // длина проблемного фрагмента
                      "original_text": string,
                      "issue_type": string,          // одно из 11
                      "explanation": string,         // почему это слабое место
                      "suggestion": string,          // как улучшить
                      "severity": "low|medium|high"
                    }
                  ],
                  "global_recommendations": [string], // 3–7 пунктов
                  "taxonomy_version": "top10-v1"
                }
                
                При невозможности анализа верни:
                {"error":"reason"}
                """,

            "combined_processing": """
                Ты — эксперт-редактор текста. Выполни комплексную обработку текста согласно заданным параметрам.
                
                ПАРАМЕТРЫ ОБРАБОТКИ: {processing_params}
                ЦЕЛЕВОЙ СТИЛЬ: {target_style}
                ЯЗЫК: {language}
                
                ЗАДАЧИ:
                {tasks}
                
                ВЕРНИ СТРОГО валидный JSON в следующем формате:
                {{
                  "processed_text": "обработанный текст",
                  "speech_time_original": число,     // время выступления для исходного текста в минутах
                  "word_count_original": число,      // количество слов в исходном тексте
                  "speech_time_final": число,        // время выступления для финального текста в минутах
                  "word_count_final": число,         // количество слов в финальном тексте
                  "changes_summary": [строка],       // список изменений
                  "processing_details": {{
                    "parasites_removed": число,
                    "bureaucracy_simplified": boolean,
                    "passive_voice_changed": boolean,
                    "structure_added": boolean,
                    "style_transformed": "стиль|null"
                  }}
                }}
                
                ИНСТРУКЦИИ ПО ОБРАБОТКЕ:
                1. Удаление слов-паразитов: убери "ну", "вот", "как бы", "в общем", "короче", "типа", "блин", "э-э", "м-м" и похожие
                2. Упрощение канцелярита: замени сложные канцелярские обороты на простые фразы
                3. Исправление пассивного залога: замени на активный залог где возможно
                4. Структурирование: добавь заголовки и логические переходы между блоками
                5. Преобразование стиля: адаптируй под указанный стиль
                
                Выполняй ТОЛЬКО те задачи, которые указаны в параметрах. Сохраняй смысл и естественность текста.
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