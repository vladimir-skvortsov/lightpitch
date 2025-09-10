import os

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# TODO: change project name, when we got the real one
PROJECT_NAME: str = 'lightpitch'

AIRTABLE_API_KEY: str = os.getenv('AIRTABLE_API_KEY', '')
AIRTABLE_BASE_ID: str = os.getenv('AIRTABLE_BASE_ID', '')

AIRTABLE_TABLES = {
    'users': 'Users',
    'pitches': 'Pitches',
    'training_sessions': 'Training_Sessions',
    'hypothetical_questions': 'Hypothetical_Questions',
}

if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
    raise ValueError('AIRTABLE_API_KEY и AIRTABLE_BASE_ID должны быть указаны в .env файле')
