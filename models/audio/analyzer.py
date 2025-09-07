"""
CLI usage:

python -m models.audio.analyzer \
  --audio data/audio/audio/test_good_1.wav \
  --script data/audio/scripts/test_good_1.txt \
  --planned_duration_sec 60 \
  --out models/audio/output/analysis_good_1_raw.json \
  --out_front models/audio/output/analysis_good_1_frontend.json


# Token can be put in .env (HUGGINGFACE_TOKEN=hf_xxx) or transferred to the flag:
  python -m models.audio.analyzer --audio data/audio/sample.wav --hf_token hf_xxx
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from sentence_transformers import SentenceTransformer, util

import librosa

from .patterns_ru import FILLERS_PATTERNS, HEDGES_PATTERNS

DEFAULT_LANGUAGE = 'ru'
DEFAULT_WHISPER_SIZE = 'small'
LONG_PAUSE_SEC = 4  # The threshold of a long pause

# The basic threshold of semantic similarity (0..1) to cover
COVERAGE_THRESHOLD = 0.65

# Dynamic threshold for short units of the script
SHORT_UNIT_WORDS = 4
SHORT_UNIT_THRESHOLD = 0.45  # Softly basic to catch formulas like "Спасибо за внимание!"


def read_text_file(path: str) -> str:
    if not path or not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def word_count(s: str) -> int:
    return len(re.findall(r"[A-Za-zА-Яа-яЁё0-9]+(?:[-'][A-Za-zА-Яа-яЁё0-9]+)?", s))


def load_audio_mono(audio_path: str, sr: int = 16000) -> Tuple[np.ndarray, int]:
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    if y.size == 0:
        return np.zeros(0, dtype=np.float32), sr
    y = np.clip(y.astype(np.float32), -1.0, 1.0)
    return y, sr


def rms_dbfs(x: np.ndarray) -> float:
    if x.size == 0:
        return None
    rms = float(np.sqrt(np.mean(np.square(x))) + 1e-12)
    return 20.0 * np.log10(rms)


def peak_dbfs(x: np.ndarray) -> float:
    if x.size == 0:
        return None
    peak = float(np.max(np.abs(x)) + 1e-12)
    return 20.0 * np.log10(peak)


def extract_segments_signal(x: np.ndarray, sr: int, segments: List[Tuple[float, float]]) -> np.ndarray:
    parts = []
    n = len(x)
    for s, e in segments:
        i = max(0, int(round(s * sr)))
        j = min(n, int(round(e * sr)))
        if j > i:
            parts.append(x[i:j])
    if parts:
        return np.concatenate(parts)
    return np.zeros(0, dtype=np.float32)


def invert_segments(total_len: int, sr: int, segments: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    total_sec = total_len / float(sr)
    segs = sorted(segments, key=lambda x: x[0])
    inv = []
    cur = 0.0
    for s, e in segs:
        s = max(0.0, s)
        e = max(s, e)
        if s > cur:
            inv.append((cur, min(s, total_sec)))
        cur = max(cur, e)
    if cur < total_sec:
        inv.append((cur, total_sec))
    # drop tiny gaps (<0.15s) - they are not representative for noise
    inv = [(s, e) for (s, e) in inv if (e - s) >= 0.15]
    return inv


def transcribe_whisper(audio_path: str, language: str, model_size: str):
    model = WhisperModel(model_size, device='cpu', compute_type='int8')
    segments_gen, info = model.transcribe(audio_path, language=language, word_timestamps=True, vad_filter=True)
    segments = list(segments_gen)
    transcript = ' '.join(s.text.strip() for s in segments)
    words = []
    for s in segments:
        if s.words:
            for w in s.words:
                if w.word is None:
                    continue
                words.append({'word': w.word.strip(), 'start': float(w.start), 'end': float(w.end)})
    total_dur = float(segments[-1].end) if segments else 0.0
    return transcript.strip(), words, segments, total_dur


def build_pyannote_vad(hf_token: Optional[str] = None):
    token = hf_token or os.getenv('HUGGINGFACE_TOKEN') or os.getenv('HF_TOKEN')
    if not token:
        raise RuntimeError(
            'Hugging Face token is required for pyannote VAD. ' 'Provide --hf_token or set HUGGINGFACE_TOKEN in .env'
        )
    try:
        return Pipeline.from_pretrained('pyannote/voice-activity-detection', token=token)
    except TypeError:
        return Pipeline.from_pretrained('pyannote/voice-activity-detection', use_auth_token=token)


def compute_speech_segments(vad_pipeline, audio_path: str) -> List[Tuple[float, float]]:
    output = vad_pipeline(audio_path)
    timeline = output.get_timeline().support()
    segs = [(float(seg.start), float(seg.end)) for seg in timeline]
    segs = sorted(segs, key=lambda x: x[0])
    return segs


def long_pauses_from_segments(speech_segs: List[Tuple[float, float]], threshold_sec: float, total_duration: float):
    spoken_time = sum(e - s for s, e in speech_segs)
    overall_time = max(total_duration, (speech_segs[-1][1] if speech_segs else 0.0))
    pauses = []
    for (s1, e1), (s2, e2) in zip(speech_segs, speech_segs[1:]):
        gap = s2 - e1
        if gap >= threshold_sec:
            pauses.append({'start': round(e1, 3), 'end': round(s2, 3), 'dur': round(gap, 3)})
    return pauses, spoken_time, overall_time


def find_patterns_with_timestamps(words, patterns):
    tokens = [re.sub(r'[^\wа-яё-]+', '', w['word'].lower()) for w in words]
    joined = ' '.join(t for t in tokens if t)
    positions = []
    acc = 0
    for i, tok in enumerate(tokens):
        if not tok:
            continue
        positions.append((acc, i))
        acc += len(tok) + 1

    def char_to_token_idx(char_pos):
        prev_idx = 0
        for acc_pos, idx in positions:
            if acc_pos <= char_pos:
                prev_idx = idx
            else:
                break
        return prev_idx

    results = []
    total = 0
    for pat in patterns:
        cnt, hits = 0, []
        for m in re.finditer(pat, joined, flags=re.IGNORECASE):
            cnt += 1
            start_idx = char_to_token_idx(m.start())
            end_idx = min(char_to_token_idx(m.end()) + 1, len(words) - 1)
            start_t = words[start_idx]['start'] if words else 0.0
            end_t = words[end_idx]['end'] if words else start_t
            hits.append({'start': round(float(start_t), 3), 'end': round(float(end_t), 3), 'text': m.group(0)})
        if cnt:
            results.append({'pattern': pat, 'count': cnt, 'occurrences': hits})
            total += cnt
    return results, total


def split_script_units(text: str):
    if not text:
        return []
    raw = re.split(r'(?:[\n\r]+|•|- |\u2022|—|–|;|\.)(?:\s+|$)', text)
    units = [u.strip() for u in raw if u and u.strip()]
    units = [u for u in units if word_count(u) >= 3]
    return units


def group_segment_texts(segments, max_seconds=12, max_words=60):
    out, buf_text = [], []
    window_start, window_end = None, None

    for s in segments:
        if window_start is None:
            window_start, window_end = s.start, s.end
        candidate = ' '.join(buf_text + [s.text.strip()])
        if (s.end - window_start) <= max_seconds and word_count(candidate) <= max_words:
            buf_text.append(s.text.strip())
            window_end = s.end
        else:
            if buf_text:
                out.append(' '.join(buf_text))
            buf_text = [s.text.strip()]
            window_start, window_end = s.start, s.end

    if buf_text:
        out.append(' '.join(buf_text))
    return out


def compute_coverage(script_text: str, seg_texts: list, threshold: float = COVERAGE_THRESHOLD):
    if not script_text or not seg_texts:
        return None
    units = split_script_units(script_text)
    if not units:
        return {'coverage': None, 'missing': [], 'matches': []}

    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    E_units = model.encode(units, normalize_embeddings=True, convert_to_tensor=True)
    E_segs = model.encode(seg_texts, normalize_embeddings=True, convert_to_tensor=True)
    sims = util.cos_sim(E_units, E_segs).cpu().numpy()

    matches, missing = [], []
    for i, unit in enumerate(units):
        unit_thr = SHORT_UNIT_THRESHOLD if word_count(unit) <= SHORT_UNIT_WORDS else threshold
        j = int(np.argmax(sims[i]))
        score = float(sims[i][j])
        if score >= unit_thr:
            matches.append(
                {'unit_idx': i, 'unit': unit, 'seg_idx': j, 'seg': seg_texts[j], 'similarity': round(score, 3)}
            )
        else:
            missing.append({'unit_idx': i, 'unit': unit, 'max_similarity': round(score, 3)})

    coverage = round(100.0 * (len(units) - len(missing)) / len(units), 1)
    return {'coverage': coverage, 'missing': missing, 'matches': matches}


def analyze_mic_quality(audio_path: str, speech_segs: List[Tuple[float, float]]) -> Dict:
    x, sr = load_audio_mono(audio_path, sr=16000)

    speech_sig = extract_segments_signal(x, sr, speech_segs)
    nonspeech_segs = invert_segments(len(x), sr, speech_segs)
    noise_sig = extract_segments_signal(x, sr, nonspeech_segs)

    speech_rms = rms_dbfs(speech_sig)
    noise_rms = rms_dbfs(noise_sig)
    peak = peak_dbfs(speech_sig)
    clip_ratio = float(np.mean(np.abs(speech_sig) >= 0.999)) if speech_sig.size else 0.0


    def color(s: str) -> str:
        return s

    if speech_rms is None:
        loud_status, loud_sub = None, None
        loud_advice = "Не удалось измерить громкость (нет речевых сегментов)."
    else:
        if clip_ratio >= 0.005 or (peak is not None and peak > -1.0):
            loud_status, loud_sub = color("error"), "clipping"
            loud_advice = "Перегруз/клиппинг. Уменьши громкость микрофона или отодвинься."
        elif speech_rms > -12.0:
            loud_status, loud_sub = color("warning"), "too_loud"
            loud_advice = "Слишком громко. Уменьши усиление/расстояние до микрофона."
        elif -23.0 <= speech_rms <= -14.0:
            loud_status, loud_sub = color("good"), "ok"
            loud_advice = "Громкость комфортная. Так держать!"
        elif -28.0 <= speech_rms < -23.0:
            loud_status, loud_sub = color("warning"), "too_quiet"
            loud_advice = "Чуть тихо. Добавь усиление микрофона или приблизься."
        else:
            loud_status, loud_sub = color("error"), "very_quiet"
            loud_advice = "Очень тихо. Проверь настройки системы/микрофона и акустику."

    loud_block = {
        "label": "Громкость речи (dBFS)",
        "speech_rms_dbfs": (None if speech_rms is None else round(speech_rms, 1)),
        "speech_peak_dbfs": (None if peak is None else round(peak, 1)),
        "clipping_ratio": round(clip_ratio, 4),
        "status": loud_status,
        "substatus": loud_sub,
        "advice": loud_advice,
        "target": "RMS −23…−14 dBFS, без клиппинга",
    }

    if (speech_rms is None) or (noise_rms is None):
        snr_status, snr_sub = None, None
        snr_db = None
        snr_advice = None
    else:
        snr_db = float(speech_rms - noise_rms)
        if snr_db >= 20.0:
            snr_status, snr_sub = color("good"), "clean"
            snr_advice = "Фон тихий, всё хорошо."
        elif 12.0 <= snr_db < 20.0:
            snr_status, snr_sub = color("warning"), "moderate_noise"
            snr_advice = "Есть заметный фон. Закрой окна/увеличь расстояние до источников шума."
        else:
            snr_status, snr_sub = color("error"), "noisy"
            snr_advice = "Сильный шум. Используй гарнитуру/шумодав и запиши в более тихом месте."

    noise_block = {
        "label": "Фоновый шум / SNR",
        "snr_db": (None if snr_db is None else round(snr_db, 1)),
        "speech_rms_dbfs": (None if speech_rms is None else round(speech_rms, 1)),
        "noise_rms_dbfs": (None if noise_rms is None else round(noise_rms, 1)),
        "status": snr_status,
        "substatus": snr_sub,
        "advice": snr_advice,
        "target": "SNR ≥ 20 dB",
    }

    return {"mic_loudness": loud_block, "mic_noise": noise_block}


def build_audio_checklist(*,
                          wpm_spoken: float,
                          long_pauses: List[Dict],
                          duration_total: float,
                          duration_spoken: float,
                          words_total: int,
                          filler_count_total: int,
                          hedge_count_total: int,
                          coverage: Optional[Dict],
                          planned_duration_sec: float,
                          speech_window_sec: float,
                          mic_quality: Dict) -> Dict[str, Dict]:

    def color(s: str) -> str:
        return s

    # Pace
    pace = float(wpm_spoken)
    pace_sub = "ok"
    if 110 <= pace <= 140:
        pace_status = color("good")
        pace_advice = "Хороший темп: держи 110–140 слов/мин, ключевые тезисы выделяй короткими паузами."
    elif 90 <= pace < 110:
        pace_status = color("warning")
        pace_sub = "too_slow"
        pace_advice = "Чуть медленно. Укороти паузы до 0.3–0.6 с, избегай растягиваний."
    elif 140 < pace <= 160:
        pace_status = color("warning")
        pace_sub = "too_fast"
        pace_advice = ("Чуть быстро. Добавляй «дыхательные» паузы 0.5–1.0 с после смысловых блоков, "
                       "делай акценты замедлением.")
    elif pace < 90:
        pace_status = color("error")
        pace_sub = "too_slow"
        pace_advice = "Сильно медленно (<90 wpm). Дроби длинные фразы, убирай протяжные звуки."
    else:
        pace_status = color("error")
        pace_sub = "too_fast"
        pace_advice = "Сильно быстро (>160 wpm). Делай пометки-паузы в тексте и контролируй дыхание."

    # Pauses
    per_min = (len(long_pauses) / (duration_total / 60.0)) if duration_total > 0 else 0.0
    max_pause = max((p["dur"] for p in long_pauses), default=0.0)

    if per_min <= 0.5 and max_pause <= 3.0:
        pauses_status, pauses_sub = color("good"), "ok"
        pauses_advice = "Хороший баланс пауз. Оставляй 1–2 короткие остановки для акцентов."
    else:
        too_many = per_min > 1.5
        too_long = max_pause > 4.0
        mid_many = (0.5 < per_min <= 1.5)
        mid_long = (3.0 < max_pause <= 4.0)

        if too_many and too_long:
            pauses_status, pauses_sub = color("error"), "many_and_long"
            pauses_advice = "Много и очень длинные паузы. Отработай переходы и дыхание."
        elif too_many:
            pauses_status, pauses_sub = color("error"), "too_many"
            pauses_advice = "Слишком часто прерываешься. Репетиция по абзацам, связки между блоками."
        elif too_long:
            pauses_status, pauses_sub = color("error"), "too_long"
            pauses_advice = "Слишком длинные паузы. Держи ключевые остановки ≤3 c, расставь их заранее."
        elif mid_many and mid_long:
            pauses_status, pauses_sub = color("warning"), "many_and_long"
            pauses_advice = "Паузы частые и длинноватые. Сократи частоту и укороти до ≤3 c."
        elif mid_many:
            pauses_status, pauses_sub = color("warning"), "too_many"
            pauses_advice = "Паузы встречаются часто. Сформируй чёткие связки между тезисами."
        elif mid_long:
            pauses_status, pauses_sub = color("warning"), "too_long"
            pauses_advice = "Паузы немного растянуты. Цель — ≤3 c на акцентах."
        else:
            pauses_status, pauses_sub = color("good"), "ok"
            pauses_advice = "Баланс пауз близок к целевому."

    # Fillers
    fillers_per_100 = (filler_count_total / max(words_total, 1)) * 100.0
    if fillers_per_100 <= 1.0:
        fillers_status, fillers_sub = color("good"), "low"
        fillers_advice = "Паразитов нет — супер! Заменяй потенциальные «э-э» короткой паузой."
    elif fillers_per_100 <= 3.0:
        fillers_status, fillers_sub = color("warning"), "medium"
        fillers_advice = "Замечены паразиты. Отрабатывай «стоп-слова» и немые паузы вместо них."
    else:
        fillers_status, fillers_sub = color("error"), "high"
        fillers_advice = "Много паразитов. Тренируй 1-мин. отрезки с самоконтролем, вырабатывай паузы."

    # Hedges
    hedges_per_100 = (hedge_count_total / max(words_total, 1)) * 100.0
    if hedges_per_100 <= 0.5:
        hedges_status, hedges_sub = color("good"), "low"
        hedges_advice = "Речь уверенная. Сохраняй конкретные формулировки."
    elif hedges_per_100 <= 1.5:
        hedges_status, hedges_sub = color("warning"), "medium"
        hedges_advice = "Чуть неуверенности. Меняй «мне кажется/думаю» на «мы сделали/показываем/планируем»."
    else:
        hedges_status, hedges_sub = color("error"), "high"
        hedges_advice = "Много неуверенности. Перепиши ключевые тезисы в утвердительной форме."

    # Coverage
    if coverage is None or coverage.get("coverage") is None:
        cov_status, cov_sub = None, None
        cov_value = None
        missing_count = None
        missing_examples = []
        cov_advice = None
    else:
        cov_value = float(coverage["coverage"])
        missing_count = len(coverage.get("missing", []))
        missing_examples = [m["unit"] for m in coverage.get("missing", [])[:3]]
        if cov_value >= 90.0:
            cov_status, cov_sub = color("good"), "ok"
            cov_advice = "Все ключевые пункты покрыты. Сфокусируйся на подаче."
        elif cov_value >= 75.0:
            cov_status, cov_sub = color("warning"), "partial"
            cov_advice = "Покрытие неполное. Пройди раздел «missing» и добавь недостающие тезисы."
        else:
            cov_status, cov_sub = color("error"), "low"
            cov_advice = "Низкое покрытие. Перестрой структуру по скрипту, начни с пропущенных пунктов."

    # Time use
    if planned_duration_sec and planned_duration_sec > 0 and speech_window_sec > 0:
        ratio = speech_window_sec / planned_duration_sec
        diff_sec = speech_window_sec - planned_duration_sec
        if 0.95 <= ratio <= 1.05:
            time_status, time_sub = color("good"), "on_time"
            time_advice = "Отличный тайминг: укладываешься в план ±5%."
        elif (0.90 <= ratio < 0.95) or (1.05 < ratio <= 1.10):
            time_status, time_sub = color("warning"), ("under_time" if ratio < 1.0 else "over_time")
            time_advice = "Чуть не попал в план (±5–10%). Подкорректируй длину примеров/пауз."
        elif ratio < 0.90:
            time_status, time_sub = color("error"), "under_time"
            time_advice = "Существенно короче плана (>10% недобор). Добавь примеры/подробности."
        else:
            time_status, time_sub = color("error"), "over_time"
            time_advice = "Существенно длиннее плана (>10% перебор). Сократи второстепенные детали."
        time_block = {
            "label": "Тайминг (план vs фактическое окно речи)",
            "planned_sec": round(planned_duration_sec, 2),
            "used_sec": round(speech_window_sec, 2),
            "diff_sec": round(diff_sec, 2),
            "ratio": round(ratio, 3),
            "status": time_status,
            "substatus": time_sub,
            "advice": time_advice,
            "target": "±5%",
        }
    else:
        time_block = {
            "label": "Тайминг (план vs фактическое окно речи)",
            "planned_sec": (None if not planned_duration_sec else round(planned_duration_sec, 2)),
            "used_sec": (None if not speech_window_sec else round(speech_window_sec, 2)),
            "diff_sec": None,
            "ratio": None,
            "status": "na",
            "substatus": "na",
            "advice": "Передайте --planned_duration_sec (>0), чтобы оценить тайминг.",
            "target": "±5%",
        }

    # Spoken ratio
    spoken_ratio = (duration_spoken / max(duration_total, 1e-6)) if duration_total else 0.0
    if 0.70 <= spoken_ratio <= 0.90:
        ratio_status, ratio_sub = color("good"), "ok"
        ratio_advice = "Баланс речи и молчания ок: речь наполнена, но есть пространство для акцентов."
    elif 0.60 <= spoken_ratio < 0.70:
        ratio_status, ratio_sub = color("warning"), "too_low"
        ratio_advice = "Много тишины. Сократи пустые паузы/заминки, делай связки между блоками."
    elif 0.90 < spoken_ratio <= 0.95:
        ratio_status, ratio_sub = color("warning"), "too_high"
        ratio_advice = "Почти без передышки. Добавь короткие паузы 0.5–1.0 c для акцентов."
    elif spoken_ratio < 0.60:
        ratio_status, ratio_sub = color("error"), "too_low"
        ratio_advice = "Слишком мало речи: много пауз/заминок. Отработай ритм и переходы."
    else:
        ratio_status, ratio_sub = color("error"), "too_high"
        ratio_advice = "Слишком плотно без дыхания. Вставляй осмысленные паузы после ключевых тезисов."

    checklist = {
        "pace": {
            "label": "Темп речи (слов/мин)",
            "value": round(pace, 1),
            "status": pace_status,
            "substatus": pace_sub,
            "advice": pace_advice,
            "target": "110–140 wpm",
        },
        "pauses": {
            "label": f"Паузы (длинные ≥ {LONG_PAUSE_SEC}с)",
            "count": len(long_pauses),
            "per_min": round(per_min, 2),
            "max_sec": round(max_pause, 2),
            "status": pauses_status,
            "substatus": pauses_sub,
            "advice": pauses_advice,
            "target": "≤0.5 шт/мин и ≤3с",
        },
        "fillers": {
            "label": "Слова-паразиты",
            "count_total": filler_count_total,
            "per_100_words": round(fillers_per_100, 2),
            "status": fillers_status,
            "substatus": fillers_sub,
            "advice": fillers_advice,
            "target": "≤1/100 слов",
        },
        "hedges": {
            "label": "Неуверенные фразы",
            "count_total": hedge_count_total,
            "per_100_words": round(hedges_per_100, 2),
            "status": hedges_status,
            "substatus": hedges_sub,
            "advice": hedges_advice,
            "target": "≤0.5/100 слов",
        },
        "coverage": {
            "label": "Покрытие скрипта (%)",
            "value": (None if coverage is None else cov_value),
            "status": cov_status,
            "substatus": cov_sub,
            "missing_count": (None if coverage is None else missing_count),
            "missing_examples": (None if coverage is None else missing_examples),
            "advice": cov_advice,
            "target": "≥90",
        },
        "time_use": time_block,
        "spoken_ratio": {
            "label": "Доля речи",
            "value": round(spoken_ratio, 3),
            "status": ratio_status,
            "substatus": ratio_sub,
            "advice": ratio_advice,
            "target": "0.70–0.90",
        },
        "mic_loudness": mic_quality["mic_loudness"],
        "mic_noise": mic_quality["mic_noise"],
    }
    return checklist


def analyze(
    audio_path: str,
    script_text: str = '',
    language: str = DEFAULT_LANGUAGE,
    whisper_size: str = DEFAULT_WHISPER_SIZE,
    pause_threshold: float = LONG_PAUSE_SEC,
    planned_duration_sec: float = 0.0,
    hf_token: Optional[str] = None,
) -> Dict:
    transcript, words, segments, total_dur = transcribe_whisper(audio_path, language, whisper_size)

    if words:
        first_word_start = min(w["start"] for w in words)
        last_word_end = max(w["end"] for w in words)
        speech_window_sec = max(0.0, float(last_word_end - first_word_start))
    else:
        first_word_start = None
        last_word_end = None
        speech_window_sec = 0.0

    vad = build_pyannote_vad(hf_token)
    speech_segs = compute_speech_segments(vad, audio_path)
    pauses, spoken_time, overall_time = long_pauses_from_segments(speech_segs, pause_threshold, total_dur)

    n_words = word_count(transcript)
    spoken_wpm = round((n_words / max(spoken_time, 1e-6)) * 60.0, 1) if spoken_time > 0 else 0.0
    overall_wpm = round((n_words / max(overall_time, 1e-6)) * 60.0, 1) if overall_time > 0 else 0.0

    fillers, fillers_total = find_patterns_with_timestamps(words, FILLERS_PATTERNS)
    hedges, hedges_total = find_patterns_with_timestamps(words, HEDGES_PATTERNS)

    seg_texts = group_segment_texts(segments, max_seconds=12, max_words=60)
    coverage = compute_coverage(script_text, seg_texts, threshold=COVERAGE_THRESHOLD) if script_text else None

    mic_quality = analyze_mic_quality(audio_path, speech_segs)

    audio_checklist = build_audio_checklist(
        wpm_spoken=spoken_wpm,
        long_pauses=pauses,
        duration_total=float(overall_time or total_dur),
        duration_spoken=float(spoken_time),
        words_total=n_words,
        filler_count_total=fillers_total,
        hedge_count_total=hedges_total,
        coverage=coverage,
        planned_duration_sec=float(planned_duration_sec or 0.0),
        speech_window_sec=float(speech_window_sec),
        mic_quality=mic_quality,
    )

    return {
        "meta": {
            "audio_path": audio_path,
            "language": language,
            "whisper_size": whisper_size,
            "pause_threshold_sec": pause_threshold,
            "coverage_threshold": COVERAGE_THRESHOLD,
            "planned_duration_sec": float(planned_duration_sec),
        },
        "transcript_text": transcript,
        "duration_sec_total": round(float(overall_time or total_dur), 2),
        "duration_sec_spoken": round(float(spoken_time), 2),
        "speech_window_start_sec": (None if first_word_start is None else round(float(first_word_start), 3)),
        "speech_window_end_sec": (None if last_word_end is None else round(float(last_word_end), 3)),
        "speech_window_sec": round(float(speech_window_sec), 2),
        "words_total": n_words,
        "wpm_overall": overall_wpm,
        "wpm_spoken": spoken_wpm,
        "speech_segments": [{"start": round(s, 3), "end": round(e, 3)} for s, e in speech_segs],
        "long_pauses": pauses,
        "filler_words": fillers,
        "filler_count_total": fillers_total,
        "hedge_phrases": hedges,
        "hedge_count_total": hedges_total,
        "script_alignment": coverage,
        "audio_checklist": audio_checklist,
    }


def analyze_file(audio_path: str, script_path: Optional[str] = None, **kwargs) -> Dict:
    script_text = read_text_file(script_path) if script_path else ""
    return analyze(audio_path=audio_path, script_text=script_text, **kwargs)


def analyze_file_frontend_format(audio_path: str, script_path: Optional[str] = None, **kwargs) -> Dict:
    analysis_result = analyze_file(audio_path, script_path, **kwargs)
    return convert_to_frontend_format(analysis_result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Path to audio file (wav/mp3/m4a...)")
    parser.add_argument("--script", help="Path to text script (optional)", default="")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="ASR language hint, e.g., ru or en")
    parser.add_argument("--whisper_size", default=DEFAULT_WHISPER_SIZE)
    parser.add_argument("--pause_threshold", type=float, default=LONG_PAUSE_SEC)
    parser.add_argument("--planned_duration_sec", type=float, required=True,
                        help="Плановая длительность выступления в секундах (обязательный параметр).")
    parser.add_argument("--hf_token", default=None, help="Hugging Face token (overrides .env)")
    parser.add_argument("--env", default=None, help="Path to .env (optional)")
    parser.add_argument("--out", default="analysis.json")
    parser.add_argument("--out_front", required=True,
                        help="Путь для сохранения результата в формате фронтенда (groups/metrics/diagnostics)")
    args = parser.parse_args()

    if args.env:
        load_dotenv(args.env, override=True)

    hf_token = args.hf_token or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
    script_text = read_text_file(args.script) if args.script else ""

    result = analyze(
        audio_path=args.audio,
        script_text=script_text,
        language=args.language,
        whisper_size=args.whisper_size,
        pause_threshold=args.pause_threshold,
        planned_duration_sec=args.planned_duration_sec,
        hf_token=hf_token,
    )
    
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved raw analysis to {args.out}")
    
    frontend_result = convert_to_frontend_format(result)
    with open(args.out_front, "w", encoding="utf-8") as f:
        json.dump(frontend_result, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved frontend format to {args.out_front}")
    
    print(f"WPM (spoken/overall): {result['wpm_spoken']} / {result['wpm_overall']}")
    print(f"Speech window vs planned: {result['speech_window_sec']}s / {result['meta']['planned_duration_sec']}s")
    if result["script_alignment"]:
        print(f"Coverage: {result['script_alignment']['coverage']}%")
    print(f"Frontend groups: {len(frontend_result['groups'])}")
    print(f"Frontend recommendations: {len(frontend_result['recommendations'])}")
    print(f"Frontend feedback: {frontend_result['feedback'][:50]}...")


def convert_to_frontend_format(analysis_result: Dict) -> Dict:
    checklist = analysis_result.get("audio_checklist", {})
    
    def calculate_pace_score(pace_value: float) -> float:
        if 110 <= pace_value <= 140:
            return 1.0 
        elif 90 <= pace_value < 110 or 140 < pace_value <= 160:
            return 0.75 
        else: 
            return 0.40 
    
    def calculate_fillers_score(fillers_per_100: float) -> float:
        if fillers_per_100 <= 1.0:
            return 1.0 
        elif fillers_per_100 <= 3.0:
            return 0.75
        else:
            return 0.40
    
    def calculate_hedges_score(hedges_per_100: float) -> float:
        if hedges_per_100 <= 0.5:
            return 1.0
        elif hedges_per_100 <= 1.5:
            return 0.75
        else:
            return 0.40
    
    def calculate_pauses_score(count: int, per_min: float, max_sec: float) -> float:
        if per_min <= 0.5 and max_sec <= 3.0:
            return 1.0
        else:
            too_many = per_min > 1.5
            too_long = max_sec > 4.0
            if too_many or too_long:
                return 0.40
            else:
                return 0.75
    
    def calculate_coverage_score(coverage_value: float) -> float:
        if coverage_value is None:
            return None
        if coverage_value >= 90.0:
            return 1.0
        elif coverage_value >= 75.0:
            return 0.75
        else:
            return 0.40
    
    def calculate_spoken_ratio_score(ratio: float) -> float:
        if 0.70 <= ratio <= 0.90:
            return 1.0
        elif 0.60 <= ratio < 0.70 or 0.90 < ratio <= 0.95:
            return 0.75
        else:
            return 0.40
    
    def calculate_timing_score(ratio: float) -> float:
        if ratio is None:
            return None
        if 0.95 <= ratio <= 1.05:
            return 1.0
        elif (0.90 <= ratio < 0.95) or (1.05 < ratio <= 1.10):
            return 0.75
        else:
            return 0.40
    
    def calculate_mic_score(rms_dbfs: float, snr_db: float) -> float:
        loudness_score = None
        if rms_dbfs is not None:
            if -23.0 <= rms_dbfs <= -14.0:
                loudness_score = 1.0
            elif (-28.0 <= rms_dbfs < -23.0) or (-14.0 < rms_dbfs <= -12.0):
                loudness_score = 0.75
            else:
                loudness_score = 0.40
        
        noise_score = None
        if snr_db is not None:
            if snr_db >= 20.0:
                noise_score = 1.0
            elif 12.0 <= snr_db < 20.0:
                noise_score = 0.75
            else:
                noise_score = 0.40
        
        scores = [s for s in [loudness_score, noise_score] if s is not None]
        return sum(scores) / len(scores) if scores else None

    pace_info = checklist.get("pace", {})
    fillers_info = checklist.get("fillers", {})
    hedges_info = checklist.get("hedges", {})
    
    pace_score = calculate_pace_score(pace_info.get("value", 0))
    fillers_score = calculate_fillers_score(fillers_info.get("per_100_words", 0))
    hedges_score = calculate_hedges_score(hedges_info.get("per_100_words", 0))
    
    speech_group = {
        "name": "Речь и артикуляция",
        "value": round((pace_score + fillers_score + hedges_score) / 3, 2),
        "metrics": [
            {
                "label": "Темп речи (слов/мин)",
                "value": pace_info.get("value", 0)
            },
            {
                "label": "Слова-паразиты на 100 слов",
                "value": fillers_info.get("per_100_words", 0)
            },
            {
                "label": "Неуверенные фразы на 100 слов", 
                "value": hedges_info.get("per_100_words", 0)
            }
        ],
        "diagnostics": [
            {
                "label": "Темп речи",
                "status": pace_info.get("substatus", "good"),
                "comment": pace_info.get("advice", "")
            },
            {
                "label": "Слова-паразиты",
                "status": fillers_info.get("substatus", "good"), 
                "comment": fillers_info.get("advice", "")
            },
            {
                "label": "Уверенность речи",
                "status": hedges_info.get("substatus", "good"),
                "comment": hedges_info.get("advice", "")
            }
        ]
    }

    pauses_info = checklist.get("pauses", {})
    coverage_info = checklist.get("coverage", {})
    spoken_ratio_info = checklist.get("spoken_ratio", {})
    
    pauses_score = calculate_pauses_score(
        pauses_info.get("count", 0),
        pauses_info.get("per_min", 0),
        pauses_info.get("max_sec", 0)
    )
    coverage_score = calculate_coverage_score(coverage_info.get("value"))
    spoken_ratio_score = calculate_spoken_ratio_score(spoken_ratio_info.get("value", 0))
    
    delivery_scores = [s for s in [pauses_score, coverage_score, spoken_ratio_score] if s is not None]
    delivery_avg = sum(delivery_scores) / len(delivery_scores) if delivery_scores else 0.6
    
    delivery_group = {
        "name": "Подача и презентация", 
        "value": round(delivery_avg, 2),
        "metrics": [
            {
                "label": "Длинные паузы (≥4с)",
                "value": pauses_info.get("count", 0)
            },
            {
                "label": "Покрытие скрипта (%)",
                "value": coverage_info.get("value", 0) if coverage_info.get("value") is not None else 0
            },
            {
                "label": "Доля речи",
                "value": round(spoken_ratio_info.get("value", 0) * 100, 1) if spoken_ratio_info.get("value") else 0
            }
        ],
        "diagnostics": [
            {
                "label": "Управление паузами",
                "status": pauses_info.get("substatus", "good"),
                "comment": pauses_info.get("advice", "")
            },
            {
                "label": "Соответствие скрипту",
                "status": coverage_info.get("substatus", "good"),
                "comment": coverage_info.get("advice", "")
            },
            {
                "label": "Баланс речи и пауз",
                "status": spoken_ratio_info.get("substatus", "good"),
                "comment": spoken_ratio_info.get("advice", "")
            }
        ]
    }

    mic_loudness_info = checklist.get("mic_loudness", {})
    mic_noise_info = checklist.get("mic_noise", {})
    time_info = checklist.get("time_use", {})
    
    mic_score = calculate_mic_score(
        mic_loudness_info.get("speech_rms_dbfs"),
        mic_noise_info.get("snr_db")
    )
    timing_score = calculate_timing_score(time_info.get("ratio"))
    
    tech_scores = [s for s in [mic_score, timing_score] if s is not None]
    tech_avg = sum(tech_scores) / len(tech_scores) if tech_scores else 0.6
    
    technical_group = {
        "name": "Технические аспекты",
        "value": round(tech_avg, 2),
        "metrics": [
            {
                "label": "Продолжительность (мин)",
                "value": round(analysis_result.get("duration_sec_total", 0) / 60, 1)
            },
            {
                "label": "Громкость речи (dBFS)",
                "value": mic_loudness_info.get("speech_rms_dbfs", 0)
            },
            {
                "label": "Соотношение сигнал/шум (dB)",
                "value": mic_noise_info.get("snr_db", 0)
            }
        ],
        "diagnostics": [
            {
                "label": "Качество записи",
                "status": mic_loudness_info.get("substatus", "good"),
                "comment": mic_loudness_info.get("advice", "")
            },
            {
                "label": "Фоновый шум",
                "status": mic_noise_info.get("substatus", "good"), 
                "comment": mic_noise_info.get("advice", "")
            },
            {
                "label": "Тайминг",
                "status": time_info.get("substatus", "good"),
                "comment": time_info.get("advice", "")
            }
        ]
    }

    all_recommendations = []
    for key in ["pace", "pauses", "fillers", "hedges", "coverage", "time_use", "spoken_ratio", "mic_loudness", "mic_noise"]:
        advice = checklist.get(key, {}).get("advice", "")
        if advice and advice not in all_recommendations:
            all_recommendations.append(advice)

    good_count = sum(1 for key in checklist if checklist[key].get("status") == "good")
    warning_count = sum(1 for key in checklist if checklist[key].get("status") == "warning") 
    error_count = sum(1 for key in checklist if checklist[key].get("status") == "error")
    
    if error_count > 2:
        feedback = "Необходимо серьёзно поработать над техникой выступления. Сфокусируйтесь на основных проблемах."
    elif warning_count > 3:
        feedback = "Хорошая основа, но есть области для улучшения. Поработайте над выявленными недостатками."
    else:
        feedback = "Отличное выступление! Минимальные корректировки помогут достичь совершенства."

    strengths = []
    areas_for_improvement = []
    
    status_mapping = {
        "pace": "Хороший темп речи",
        "pauses": "Оптимальное использование пауз", 
        "fillers": "Минимум слов-паразитов",
        "hedges": "Уверенная манера речи",
        "coverage": "Полное покрытие материала",
        "time_use": "Отличный тайминг",
        "spoken_ratio": "Хороший баланс речи и пауз",
        "mic_loudness": "Качественный звук",
        "mic_noise": "Чистая запись без шумов"
    }
    
    improvement_mapping = {
        "pace": "Работа над темпом речи",
        "pauses": "Управление паузами",
        "fillers": "Устранение слов-паразитов", 
        "hedges": "Повышение уверенности речи",
        "coverage": "Улучшение покрытия материала",
        "time_use": "Работа с таймингом",
        "spoken_ratio": "Баланс речи и пауз",
        "mic_loudness": "Качество звука",
        "mic_noise": "Устранение фонового шума"
    }
    
    for key, description in status_mapping.items():
        status = checklist.get(key, {}).get("status", "")
        if status == "good":
            strengths.append(description)
        elif status in ["warning", "error"]:
            areas_for_improvement.append(improvement_mapping[key])

    return {
        "groups": [speech_group, delivery_group, technical_group],
        "recommendations": all_recommendations[:6],
        "feedback": feedback,
        "strengths": strengths,
        "areas_for_improvement": areas_for_improvement
    }


if __name__ == "__main__":
    main()
