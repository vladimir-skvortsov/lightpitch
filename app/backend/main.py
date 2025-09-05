from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

from config import PROJECT_NAME
from db_models import Pitch, PitchCreate, PitchUpdate
from pitches import (
    create_pitch as create_pitch_service,
    get_pitch as get_pitch_service,
    list_pitches as list_pitches_service,
    update_pitch as update_pitch_service,
    delete_pitch as delete_pitch_service,
)


app = FastAPI(title=PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# CRUD operations for pitches
@app.post('/api/v1/pitches/', response_model=Pitch)
async def create_pitch_endpoint(pitch: PitchCreate):
    """Create a new pitch"""
    return create_pitch_service(pitch)


@app.get('/api/v1/pitches/', response_model=list[Pitch])
async def get_all_pitches():
    """Get all pitches"""
    return list_pitches_service()


@app.get('/api/v1/pitches/{pitch_id}', response_model=Pitch)
async def get_pitch_endpoint(pitch_id: str):
    """Get a specific pitch by ID"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return pitch


@app.put('/api/v1/pitches/{pitch_id}', response_model=Pitch)
async def update_pitch_endpoint(pitch_id: str, pitch_update: PitchUpdate):
    """Update an existing pitch"""
    updated_pitch = update_pitch_service(pitch_id, pitch_update)
    if not updated_pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return updated_pitch


@app.delete('/api/v1/pitches/{pitch_id}')
async def delete_pitch_endpoint(pitch_id: str):
    """Delete a pitch"""
    deleted_pitch = delete_pitch_service(pitch_id)
    if not deleted_pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return {'message': f"Pitch '{deleted_pitch.title}' has been deleted successfully"}


# AI endpoints
@app.post('/api/v1/score/pitch')
async def score_pitch(video: UploadFile = File(...), pitch_id: Optional[str] = Form(None)):
    """Analyze pitch video and return hardcoded results"""

    # Validate video file
    content_type = video.content_type or ''
    if not content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail='File must be a video')

    # Check file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    video_content = await video.read()
    if len(video_content) > max_size:
        raise HTTPException(status_code=400, detail='File size must be less than 100MB')

    # TODO: Интеграция с AI для анализа видео
    # Пока возвращаем hardcoded результаты

    import random
    import time

    time.sleep(1)

    base_score = random.uniform(6.5, 9.0)

    return {
        'overall_score': round(base_score, 1),
        'confidence': round(base_score + random.uniform(-0.5, 0.3), 1),
        'clarity': round(base_score + random.uniform(-0.3, 0.5), 1),
        'pace': round(base_score + random.uniform(-0.8, 0.2), 1),
        'engagement': round(base_score + random.uniform(-0.2, 0.7), 1),
        'body_language': round(base_score + random.uniform(-0.6, 0.4), 1),
        'eye_contact': round(base_score + random.uniform(-0.4, 0.6), 1),
        'voice_tone': round(base_score + random.uniform(-0.3, 0.4), 1),
        'duration': f'{random.randint(1, 5)}:{random.randint(10, 59):02d}',
        'word_count': random.randint(150, 450),
        'feedback': [
            {
                'type': 'positive',
                'message': random.choice(
                    [
                        'Отличная четкость речи и хорошая интонация',
                        'Уверенная подача материала',
                        'Хороший зрительный контакт с аудиторией',
                        'Профессиональная манера речи',
                    ]
                ),
            },
            {
                'type': 'improvement',
                'message': random.choice(
                    [
                        'Рекомендуется немного замедлить темп речи для лучшего восприятия',
                        'Добавьте больше жестов для усиления эмоциональной составляющей',
                        'Используйте больше пауз для акцентирования важных моментов',
                        'Увеличьте эмоциональную вовлеченность',
                    ]
                ),
            },
            {
                'type': 'positive',
                'message': random.choice(
                    ['Хорошая структура выступления', 'Логичное изложение материала', 'Удачные примеры и аналогии']
                ),
            },
        ],
        'strengths': [
            'Четкая артикуляция',
            'Хорошая структура выступления',
            'Уверенная подача материала',
            'Профессиональная манера речи',
        ],
        'areas_for_improvement': [
            'Темп речи',
            'Язык тела и жестикуляция',
            'Паузы для акцентирования',
            'Эмоциональная вовлеченность',
        ],
    }


@app.post('/api/v1/score/text')
async def score_text():
    return {}


@app.post('/api/v1/score/presentation')
async def score_presentation():
    return {}
