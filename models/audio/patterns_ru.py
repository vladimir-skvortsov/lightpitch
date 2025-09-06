"""
Russian templates for:
- parasitic words (fillers_patterns)
- uncertain formulations/Hedges (Hedges_patterns)

Regularities are matched according to the normalized text of the transcript
(the lower register, the signs are removed), and then it will stroke back to the timcode of the words.
"""

FILLERS_PATTERNS = [
    r'\bэ+м?\b',
    r'\bэм+\b',
    r'\bм-?м\b',
    r'\bну\b',
    r'\bвот\b',
    r'\bкак бы\b',
    r'\bтипа\b',
    r'\bкороче\b',
    r'\bзначит\b',
    r'\bв общем\b',
    r'\bпо сути\b',
    r'\bтак сказать\b',
    r'\bсобственно\b',
    r'\bполучается\b',
]

HEDGES_PATTERNS = [
    r'\bмне кажется\b',
    r'\bкажется\b',
    r'\bя думаю\b',
    r'\bвозможно\b',
    r'\bскорее всего\b',
    r'\bнаверное\b',
    r'\bпо-моему\b',
    r'\bможет быть\b',
    r'\bя не уверен[ао]?\b',
    r'\bзатрудняюсь\b',
    r'\bполагаю\b',
    r'\bвроде\b',
]
