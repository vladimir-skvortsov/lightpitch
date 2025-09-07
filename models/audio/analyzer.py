"""
CLI usage:

python -m models.audio.analyzer \
  --audio data/audio/audio/test_good_1.wav \
  --script data/audio/scripts/test_good_1.txt \
  --planned_duration_sec 60 \
  --out models/audio/output/analysis_good_1.json

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
                          speech_window_sec: float) -> Dict[str, Dict]:

    def color(s: str) -> str:
        return s

    # Pace
    pace = float(wpm_spoken)
    pace_sub = "ok"
    if 110 <= pace <= 140:
        pace_status = color("good")
        pace_advice = "Хороший темп: держи 110–140 слов/мин, ключевые тезисы выделяй короткими паузами."
    elif 90 <= pace < 110:
        pace_status = color("warning"); pace_sub = "too_slow"
        pace_advice = "Чуть медленно. Укороти паузы до 0.3–0.6 с, избегай растягиваний."
    elif 140 < pace <= 160:
        pace_status = color("warning"); pace_sub = "too_fast"
        pace_advice = ("Чуть быстро. Добавляй «дыхательные» паузы 0.5–1.0 с после смысловых блоков, "
                       "делай акценты замедлением.")
    elif pace < 90:
        pace_status = color("error"); pace_sub = "too_slow"
        pace_advice = "Сильно медленно (<90 wpm). Дроби длинные фразы, убирай протяжные звуки"
    else:
        pace_status = color("error"); pace_sub = "too_fast"
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

    return {
        "pace": {
            "label": "Темп речи (слов/мин)",
            "value": round(pace, 1),
            "status": pace_status,
            "substatus": pace_sub,
            "advice": pace_advice,
            "target": "110–140 wpm",
        },
        "pauses": {
            "label": "Паузы (длинные ≥ {}с)".format(LONG_PAUSE_SEC),
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
    }


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
    print(f"[OK] Saved results to {args.out}")
    print(f"WPM (spoken/overall): {result['wpm_spoken']} / {result['wpm_overall']}")
    print(f"Speech window vs planned: {result['speech_window_sec']}s / {result['meta']['planned_duration_sec']}s")
    if result["script_alignment"]:
        print(f"Coverage: {result['script_alignment']['coverage']}%")
    print(f"Fillers: {result['filler_count_total']}, Hedges: {result['hedge_count_total']}")


if __name__ == "__main__":
    main()
