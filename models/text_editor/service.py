import json
import logging
from typing import Any, Dict, List, Tuple

from .normalizers import normalize_weak_spot
from .openrouter_client import OpenRouterService
from .prompts import COMBINED_PROCESSING_PROMPT, WEAK_SPOTS_PROMPT, FEEDBACK_GENERATION_PROMPT
from .types import AnalysisType, TextStyle, WeakSpot

logger = logging.getLogger(__name__)


class TextAnalysisService:
    def __init__(self):
        self.openai_service = OpenRouterService()
        self.prompts = {
            'weak_spots': WEAK_SPOTS_PROMPT,
            'combined_processing': COMBINED_PROCESSING_PROMPT,
            'feedback_generation': FEEDBACK_GENERATION_PROMPT,
        }

    async def analyze_weak_spots(self, text: str, language: str) -> Tuple[List[WeakSpot], List[str]]:
        prompt = self.prompts['weak_spots'].replace('{{LANG}}', language)
        response = await self.openai_service.analyze_text(prompt, text, expect_json=True)
        try:
            data = json.loads(response)
            raw_spots = data.get('weak_spots', [])
            weak_spots = [WeakSpot(**normalize_weak_spot(spot)) for spot in raw_spots]
            recommendations = data.get('global_recommendations', [])
            return weak_spots, recommendations
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f'Failed to parse weak spots response: {e}')
            return [], ['Не удалось обработать анализ слабых мест']

    async def process_text_combined(
        self, text: str, analysis_types: List[AnalysisType], style: TextStyle | None, language: str
    ) -> Dict[str, Any]:
        processing_params: List[str] = []
        tasks: List[str] = []

        if AnalysisType.REMOVE_PARASITES in analysis_types:
            processing_params.append('remove_parasites')
            tasks.append('- Удали слова-паразиты, сохранив естественность')
        if AnalysisType.REMOVE_BUREAUCRACY in analysis_types:
            processing_params.append('remove_bureaucracy')
            tasks.append('- Упрости канцелярские обороты и бюрократические выражения')
        if AnalysisType.REMOVE_PASSIVE in analysis_types:
            processing_params.append('remove_passive')
            tasks.append('- Замени пассивный залог на активный где возможно')
        if AnalysisType.STRUCTURE_BLOCKS in analysis_types:
            processing_params.append('structure_blocks')
            tasks.append('- Структурируй текст по смысловым блокам с заголовками')
        if AnalysisType.STYLE_TRANSFORM in analysis_types and style:
            processing_params.append('style_transform')
            style_descriptions = {
                TextStyle.CASUAL: 'неформальный, разговорный',
                TextStyle.PROFESSIONAL: 'профессиональный, деловой',
                TextStyle.SCIENTIFIC: 'научный, академический',
            }
            tasks.append(f"- Преобразуй в {style_descriptions.get(style, 'указанный')} стиль")

        tasks.append('- Рассчитай время выступления для исходного и финального текста')

        processing_params_str = ', '.join(processing_params)
        target_style_str = style.value if style else 'не изменять'
        tasks_str = '\n'.join(tasks)

        prompt = self.prompts['combined_processing'].format(
            processing_params=processing_params_str,
            target_style=target_style_str,
            language=language,
            tasks=tasks_str,
        )

        response = await self.openai_service.analyze_text(prompt, text, expect_json=True)
        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f'Failed to parse combined processing response: {e}')
            words = len(text.split())
            speech_time = words / 150
            return {
                'processed_text': text,
                'speech_time_original': speech_time,
                'word_count_original': words,
                'speech_time_final': speech_time,
                'word_count_final': words,
                'changes_summary': ['Обработка не удалась'],
                'processing_details': {
                    'parasites_removed': 0,
                    'bureaucracy_simplified': False,
                    'passive_voice_changed': False,
                    'structure_added': False,
                    'style_transformed': None,
                },
            }

    def _score_by_issue_density(self, issues_count: int, words: int, weight: float = 1.0) -> float:
        words_safe = max(1, words)
        density = (issues_count * 1000.0) / words_safe
        penalty = min(0.6, (density / 50.0) * weight)
        return max(0.4, 1.0 - penalty)

    def _build_group(self, name: str, value: float, diagnostics: list, metrics: list) -> Dict[str, Any]:
        return {
            'name': name,
            'value': round(value, 2),
            'metrics': metrics,
            'diagnostics': diagnostics,
        }

    async def generate_feedback(self, text: str, weak_spots: List[WeakSpot], recommendations: List[str], language: str) -> Dict[str, Any]:
        """Generate dynamic feedback based on analysis results"""
        words = len(text.split())
        speech_time_min = round(words / 150.0, 2)
        
        # Prepare summary of weak spots by type
        by_type = {}
        for ws in weak_spots:
            by_type.setdefault(ws.issue_type, []).append(ws)
        
        weak_spots_summary = []
        for issue_type, spots in by_type.items():
            count = len(spots)
            issue_names = {
                'punctuation_error': 'ошибки пунктуации',
                'filler': 'слова-паразиты', 
                'bureaucracy': 'канцеляризмы',
                'passive_overuse': 'пассивный залог',
                'logic_gap': 'логические разрывы',
                'clarity': 'неясные формулировки',
                'redundancy': 'повторы',
                'tone_mismatch': 'несоответствие тона',
                'term_misuse': 'неверное использование терминов',
                'wordiness': 'избыточная длина предложений',
                'other': 'другие проблемы'
            }
            issue_name = issue_names.get(issue_type, issue_type)
            weak_spots_summary.append(f"{count} {issue_name}")
        
        weak_spots_str = ', '.join(weak_spots_summary) if weak_spots_summary else 'проблем не найдено'
        recommendations_str = ', '.join(recommendations[:3]) if recommendations else 'специальных рекомендаций нет'
        
        prompt = self.prompts['feedback_generation'].format(
            language=language,
            weak_spots_summary=weak_spots_str,
            recommendations_summary=recommendations_str,
            word_count=words,
            speech_time_minutes=speech_time_min
        )
        
        try:
            response = await self.openai_service.analyze_text(prompt, text, expect_json=True)
            return json.loads(response)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f'Failed to parse feedback generation response: {e}')
            # Fallback to basic feedback
            if weak_spots:
                return {
                    'feedback': f'Текст содержит {len(weak_spots)} проблемных мест. Рекомендуется переработать текст для улучшения качества.',
                    'strengths': ['Текст имеет базовую структуру'],
                    'areas_for_improvement': ['Устранение найденных проблем', 'Улучшение стиля изложения']
                }
            else:
                return {
                    'feedback': 'Текст в целом хорошо структурирован и не содержит серьезных проблем.',
                    'strengths': ['Хорошая структура', 'Отсутствие серьезных ошибок'],
                    'areas_for_improvement': []
                }

    async def get_legacy_interface(self, text: str, language: str) -> Dict[str, Any]:
        weak_spots, recommendations = await self.analyze_weak_spots(text, language)
        words = len(text.split())
        speech_time_min = round(words / 150.0, 2)

        by_type: Dict[str, list] = {}
        for ws in weak_spots:
            by_type.setdefault(ws.issue_type, []).append(ws)

        def diag_from_spots(spots: list, ok_label: str) -> list:
            if not spots:
                return [
                    {
                        'label': ok_label,
                        'status': 'good',
                        'comment': None,
                    }
                ]
            diags = []
            for s in spots[:10]:
                diags.append(
                    {
                        'label': s.original_text[:50] + ('...' if len(s.original_text) > 50 else ''),
                        'status': 'error' if s.severity == 'high' else 'warning',
                        'sublabel': None,
                        'comment': s.suggestion or s.explanation,
                    }
                )
            return diags

        ortho_spots = by_type.get('punctuation_error', [])
        ortho_value = self._score_by_issue_density(len(ortho_spots), words, weight=1.0)
        ortho_metrics = [
            {'label': 'Ошибки пунктуации', 'value': len(ortho_spots)},
            {'label': 'Количество слов', 'value': words},
            {'label': 'Время речи (мин)', 'value': speech_time_min},
        ]
        ortho_group = self._build_group(
            'Орфография и пунктуация', ortho_value, diag_from_spots(ortho_spots, 'Ошибок не обнаружено'), ortho_metrics
        )

        filler_spots = by_type.get('filler', [])
        filler_value = self._score_by_issue_density(len(filler_spots), words, weight=1.2)
        filler_metrics = [{'label': 'Встречи слов‑паразитов', 'value': len(filler_spots)}]
        filler_group = self._build_group(
            'Слова‑паразиты', filler_value, diag_from_spots(filler_spots, 'Паразитов не обнаружено'), filler_metrics
        )

        bur_spots = by_type.get('bureaucracy', [])
        bur_value = self._score_by_issue_density(len(bur_spots), words, weight=1.1)
        bur_metrics = [{'label': 'Канцеляризмов', 'value': len(bur_spots)}]
        bur_group = self._build_group(
            'Канцеляризмы', bur_value, diag_from_spots(bur_spots, 'Канцеляризмов не обнаружено'), bur_metrics
        )

        passive_spots = by_type.get('passive_overuse', [])
        passive_value = self._score_by_issue_density(len(passive_spots), words, weight=1.0)
        passive_metrics = [{'label': 'Случаи пассивного залога', 'value': len(passive_spots)}]
        passive_group = self._build_group(
            'Пассивный залог',
            passive_value,
            diag_from_spots(passive_spots, 'Нет избыточного пассивного залога'),
            passive_metrics,
        )

        structure_spots = by_type.get('logic_gap', [])
        structure_value = self._score_by_issue_density(len(structure_spots), words, weight=1.3)
        structure_metrics = [{'label': 'Логические разрывы', 'value': len(structure_spots)}]
        structure_group = self._build_group(
            'Структура',
            structure_value,
            diag_from_spots(structure_spots, 'Логических разрывов не обнаружено'),
            structure_metrics,
        )

        groups = [
            ortho_group,
            bur_group,
            filler_group,
            passive_group,
            structure_group,
        ]

        # Generate dynamic feedback using AI
        feedback_data = await self.generate_feedback(text, weak_spots, recommendations, language)
        
        return {
            'groups': groups,
            'feedback': feedback_data.get('feedback', 'Анализ завершен'),
            'strengths': feedback_data.get('strengths', []),
            'areas_for_improvement': feedback_data.get('areas_for_improvement', []),
            'recommendations': recommendations[:7],
        }
