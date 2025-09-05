from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from typing import Optional
import os
import uuid
import shutil

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

# Create directories for file uploads
UPLOAD_DIR = 'uploads'
PRESENTATIONS_DIR = os.path.join(UPLOAD_DIR, 'presentations')
os.makedirs(PRESENTATIONS_DIR, exist_ok=True)

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


# Presentation file endpoints
@app.post('/api/v1/pitches/{pitch_id}/presentation')
async def upload_presentation(pitch_id: str, file: UploadFile = File(...)):
    """Upload a presentation file for a pitch"""

    # Check if pitch exists
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    # Validate file type
    allowed_types = [
        'application/pdf',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    ]
    content_type = file.content_type or ''

    if not any(content_type.startswith(t) for t in allowed_types):
        raise HTTPException(status_code=400, detail='File must be a presentation (PDF, PPT, PPTX)')

    # Generate unique filename
    file_extension = os.path.splitext(file.filename or '')[1]
    unique_filename = f'{uuid.uuid4()}{file_extension}'
    file_path = os.path.join(PRESENTATIONS_DIR, unique_filename)

    try:
        # Save file
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update pitch with presentation info
        pitch_update = PitchUpdate(presentation_file_name=file.filename, presentation_file_path=unique_filename)
        updated_pitch = update_pitch_service(pitch_id, pitch_update)

        return {'message': 'Presentation uploaded successfully', 'filename': file.filename}

    except Exception as e:
        # Clean up file if database update fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f'Error uploading presentation: {str(e)}')


@app.get('/api/v1/pitches/{pitch_id}/presentation')
async def get_presentation(pitch_id: str):
    """Download the presentation file for a pitch"""

    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_path:
        raise HTTPException(status_code=404, detail='No presentation file found for this pitch')

    file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='Presentation file not found on disk')

    return FileResponse(
        path=file_path,
        filename=pitch.presentation_file_name or 'presentation.pdf',
        media_type='application/octet-stream',
    )


@app.delete('/api/v1/pitches/{pitch_id}/presentation')
async def delete_presentation(pitch_id: str):
    """Delete the presentation file for a pitch"""

    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_path:
        raise HTTPException(status_code=404, detail='No presentation file found for this pitch')

    # Remove file from disk
    file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Update pitch to remove presentation info
    pitch_update = PitchUpdate(presentation_file_name=None, presentation_file_path=None)
    update_pitch_service(pitch_id, pitch_update)

    return {'message': 'Presentation deleted successfully'}


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
