from typing import Any, Dict, Set

ALLOWED_ISSUE_TYPES: Set[str] = {
    'clarity',
    'redundancy',
    'bureaucracy',
    'filler',
    'passive_overuse',
    'logic_gap',
    'tone_mismatch',
    'term_misuse',
    'punctuation_error',
    'wordiness',
    'other',
}

ALLOWED_SEVERITY: Set[str] = {'low', 'medium', 'high'}


def normalize_weak_spot(raw: Dict[str, Any]) -> Dict[str, Any]:
    spot = dict(raw)

    pos = spot.get('position')
    if isinstance(pos, str):
        try:
            spot['position'] = int(float(pos))
        except ValueError:
            spot['position'] = 0
    elif isinstance(pos, float):
        spot['position'] = int(pos)
    elif not isinstance(pos, int):
        spot['position'] = 0

    length_val = spot.get('length')
    if isinstance(length_val, str):
        try:
            spot['length'] = int(float(length_val))
        except ValueError:
            spot['length'] = None
    elif isinstance(length_val, float):
        spot['length'] = int(length_val)
    elif not isinstance(length_val, int):
        spot['length'] = None

    spot.setdefault('explanation', None)

    issue_type = (spot.get('issue_type') or '').strip()
    spot['issue_type'] = issue_type if issue_type in ALLOWED_ISSUE_TYPES else 'other'

    severity = (spot.get('severity') or '').strip().lower()
    spot['severity'] = severity if severity in ALLOWED_SEVERITY else 'medium'

    return spot


def get_issue_title(issue_type: str) -> str:
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
        'other': 'Другие проблемы',
    }
    return titles.get(issue_type, 'Проблема текста')


def get_category_name(issue_type: str) -> str:
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
        'other': 'Общее',
    }
    return categories.get(issue_type, 'Общее')


def add_good_practices(good_practices: list, issues_found: set, text: str):
    if 'logic_gap' not in issues_found:
        good_practices.append(
            {
                'title': 'Четкая структура выступления',
                'description': 'Выступление имеет логичную последовательность идей',
                'category': 'Структура',
            }
        )
    if 'clarity' not in issues_found:
        good_practices.append(
            {
                'title': 'Понятная формулировка идей',
                'description': 'Основные мысли изложены четко и доступно',
                'category': 'Содержание',
            }
        )
    if 'wordiness' not in issues_found and 'redundancy' not in issues_found:
        good_practices.append(
            {
                'title': 'Краткость изложения',
                'description': 'Информация представлена без лишних слов',
                'category': 'Стиль',
            }
        )
    if 'filler' not in issues_found:
        good_practices.append(
            {
                'title': 'Чистая речь',
                'description': 'Отсутствуют слова-паразиты и лишние элементы',
                'category': 'Лексика',
            }
        )
    if any(word in text.lower() for word in ['рекомендую', 'предлагаю', 'призываю', 'действие', 'решение']):
        good_practices.append(
            {
                'title': 'Призыв к действию',
                'description': 'В выступлении есть четкие рекомендации',
                'category': 'Заключение',
            }
        )
    if any(word in text.lower() for word in ['например', 'пример', 'случай', 'ситуация']):
        good_practices.append(
            {
                'title': 'Использование примеров',
                'description': 'Для иллюстрации используются конкретные примеры',
                'category': 'Содержание',
            }
        )
    if 'tone_mismatch' not in issues_found:
        good_practices.append(
            {
                'title': 'Подходящий тон',
                'description': 'Стиль изложения соответствует цели выступления',
                'category': 'Стиль',
            }
        )
    if 'passive_overuse' not in issues_found:
        good_practices.append(
            {
                'title': 'Активная форма изложения',
                'description': 'Преобладает активный залог, что делает речь динамичной',
                'category': 'Грамматика',
            }
        )
