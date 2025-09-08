import uuid
from datetime import datetime
from typing import List
import random

from db import (
    get_hypothetical_question_by_id,
    get_hypothetical_questions_by_pitch_id,
    get_all_hypothetical_questions,
    store_hypothetical_question,
    delete_hypothetical_question_by_id,
    hypothetical_question_exists,
    get_pitch_by_id,
)
from db_models import (
    HypotheticalQuestion,
    HypotheticalQuestionCreate,
    HypotheticalQuestionUpdate,
    QuestionCategory,
    QuestionDifficulty,
)


def create_hypothetical_question(question_data: HypotheticalQuestionCreate) -> HypotheticalQuestion:
    """Create a new hypothetical question"""
    question_id = str(uuid.uuid4())
    now = datetime.now()

    new_question = HypotheticalQuestion(
        id=question_id,
        pitch_id=question_data.pitch_id,
        question_text=question_data.question_text,
        category=question_data.category,
        difficulty=question_data.difficulty,
        suggested_answer=question_data.suggested_answer,
        context=question_data.context,
        preparation_tips=question_data.preparation_tips or [],
        created_at=now,
        updated_at=now,
    )

    return store_hypothetical_question(new_question)


def get_hypothetical_question(question_id: str) -> HypotheticalQuestion | None:
    """Get a hypothetical question by ID"""
    return get_hypothetical_question_by_id(question_id)


def get_hypothetical_questions_for_pitch(pitch_id: str) -> List[HypotheticalQuestion]:
    """Get all hypothetical questions for a specific pitch"""
    questions = get_hypothetical_questions_by_pitch_id(pitch_id)
    # Sort by creation date (newest first)
    return sorted(questions, key=lambda x: x.created_at, reverse=True)


def list_hypothetical_questions() -> List[HypotheticalQuestion]:
    """Get all hypothetical questions"""
    return get_all_hypothetical_questions()


def update_hypothetical_question(
    question_id: str, question_update: HypotheticalQuestionUpdate
) -> HypotheticalQuestion | None:
    """Update an existing hypothetical question"""
    existing_question = get_hypothetical_question_by_id(question_id)
    if not existing_question:
        return None

    # Update only the fields that are provided
    update_data = question_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing_question, field, value)

    existing_question.updated_at = datetime.now()
    return store_hypothetical_question(existing_question)


def delete_hypothetical_question(question_id: str) -> HypotheticalQuestion | None:
    """Delete a hypothetical question"""
    if not hypothetical_question_exists(question_id):
        return None

    return delete_hypothetical_question_by_id(question_id)


def generate_hypothetical_questions_for_pitch(pitch_id: str, count: int = 5) -> List[HypotheticalQuestion]:
    """Generate hypothetical questions based on pitch content"""
    pitch = get_pitch_by_id(pitch_id)
    if not pitch:
        return []

    # For demo purposes, create sample questions
    # In a real implementation, this would use AI to generate contextual questions
    sample_questions = [
        {
            'text': 'Как вы планируете масштабировать этот проект?',
            'category': QuestionCategory.STRATEGY,
            'difficulty': QuestionDifficulty.MEDIUM,
            'context': 'Вопрос о долгосрочном планировании и росте проекта',
            'tips': [
                'Подготовьте конкретные цифры роста',
                'Опишите ключевые этапы развития',
                'Упомяните необходимые ресурсы',
            ],
        },
        {
            'text': 'Какова ваша целевая аудитория?',
            'category': QuestionCategory.MARKET,
            'difficulty': QuestionDifficulty.EASY,
            'context': 'Базовое понимание рынка и клиентов',
            'tips': ['Четко определите демографию', 'Приведите размер рынка', 'Объясните, почему именно эта аудитория'],
        },
        {
            'text': 'Как вы планируете монетизировать проект?',
            'category': QuestionCategory.BUSINESS,
            'difficulty': QuestionDifficulty.MEDIUM,
            'context': 'Вопрос о бизнес-модели и источниках дохода',
            'tips': [
                'Опишите основные источники дохода',
                'Приведите прогнозы выручки',
                'Объясните модель ценообразования',
            ],
        },
        {
            'text': 'Кто ваши основные конкуренты?',
            'category': QuestionCategory.MARKET,
            'difficulty': QuestionDifficulty.EASY,
            'context': 'Анализ конкурентной среды',
            'tips': ['Назовите 3-5 основных конкурентов', 'Объясните ваши преимущества', 'Покажите анализ конкурентов'],
        },
        {
            'text': 'Какие технические риски вы видите?',
            'category': QuestionCategory.TECHNICAL,
            'difficulty': QuestionDifficulty.HARD,
            'context': 'Понимание технических вызовов проекта',
            'tips': [
                'Честно признайте возможные сложности',
                'Предложите пути решения',
                'Покажите план минимизации рисков',
            ],
        },
        {
            'text': 'Сколько денег вам нужно и на что?',
            'category': QuestionCategory.FINANCE,
            'difficulty': QuestionDifficulty.MEDIUM,
            'context': 'Финансовые потребности проекта',
            'tips': ['Дайте четкую сумму', 'Распишите статьи расходов', 'Обоснуйте каждую крупную трату'],
        },
        {
            'text': 'Какой опыт у команды проекта?',
            'category': QuestionCategory.TEAM,
            'difficulty': QuestionDifficulty.EASY,
            'context': 'Вопрос о компетенциях команды',
            'tips': ['Выделите ключевые достижения', 'Покажите релевантный опыт', 'Упомяните уникальные навыки'],
        },
        {
            'text': 'Что будет, если проект не сработает?',
            'category': QuestionCategory.STRATEGY,
            'difficulty': QuestionDifficulty.HARD,
            'context': 'План действий в случае неудачи',
            'tips': ['Покажите альтернативные сценарии', 'Обсудите план отступления', 'Продемонстрируйте гибкость'],
        },
    ]

    # Randomly select questions and create them
    selected_questions = random.sample(sample_questions, min(count, len(sample_questions)))
    created_questions = []

    for q_data in selected_questions:
        question_create = HypotheticalQuestionCreate(
            pitch_id=pitch_id,
            question_text=q_data['text'],
            category=q_data['category'],
            difficulty=q_data['difficulty'],
            context=q_data['context'],
            preparation_tips=q_data['tips'],
        )
        created_question = create_hypothetical_question(question_create)
        created_questions.append(created_question)

    return created_questions


def get_hypothetical_questions_stats(pitch_id: str) -> dict:
    """Get statistics for hypothetical questions of a specific pitch"""
    questions = get_hypothetical_questions_by_pitch_id(pitch_id)

    if not questions:
        return {
            'total_count': 0,
            'by_category': {},
            'by_difficulty': {},
            'latest_question': None,
        }

    # Count by category
    category_counts: dict[str, int] = {}
    for question in questions:
        category = question.category.value
        category_counts[category] = category_counts.get(category, 0) + 1

    # Count by difficulty
    difficulty_counts: dict[str, int] = {}
    for question in questions:
        difficulty = question.difficulty.value
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

    # Get the latest question
    latest_question = max(questions, key=lambda x: x.created_at) if questions else None

    return {
        'total_count': len(questions),
        'by_category': category_counts,
        'by_difficulty': difficulty_counts,
        'latest_question': {
            'id': latest_question.id,
            'question_text': latest_question.question_text[:100] + '...'
            if len(latest_question.question_text) > 100
            else latest_question.question_text,
            'category': latest_question.category.value,
            'difficulty': latest_question.difficulty.value,
            'created_at': latest_question.created_at,
        }
        if latest_question
        else None,
    }
