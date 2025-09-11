import random
import uuid
from datetime import datetime
from typing import List

from db import (
    delete_hypothetical_question_by_id,
    get_all_hypothetical_questions,
    get_hypothetical_question_by_id,
    get_hypothetical_questions_by_pitch_id,
    hypothetical_question_exists,
    store_hypothetical_question,
)
from db_models import (
    HypotheticalQuestion,
    HypotheticalQuestionUpdate,
)


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
