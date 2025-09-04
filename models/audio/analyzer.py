"""
CLI usage:

python -m models.audio.analyzer \
  --audio data/audio/audio/test_good_1.wav \
  --script data/audio/scripts/test_good_1.txt \
  --language ru \
  --out models/audio/output/analysis_good_1.json

# Token can be put in .env (HUGGINGFACE_TOKEN=hf_xxx) or transferred to the flag:
  python -m models.audio.analyzer --audio data/audio/sample.wav --hf_token hf_xxx
"""

from __future__ import annotations
import os
import re
import json
import argparse
import numpy as np
from typing import List, Dict, Tuple, Optional

from dotenv import load_dotenv
load_dotenv()

from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from sentence_transformers import SentenceTransformer, util
from .patterns_ru import FILLERS_PATTERNS, HEDGES_PATTERNS


DEFAULT_LANGUAGE = "ru"
DEFAULT_WHISPER_SIZE = "small"
LONG_PAUSE_SEC = 2           # The threshold of a long pause

# The basic threshold of semantic similarity (0..1) to cover
COVERAGE_THRESHOLD = 0.65

# Dynamic threshold for short units of the script
SHORT_UNIT_WORDS = 4
SHORT_UNIT_THRESHOLD = 0.45     # Softly basic to catch formulas like "Спасибо за внимание!"


def read_text_file(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def word_count(s: str) -> int:
    return len(re.findall(r"[A-Za-zА-Яа-яЁё0-9]+(?:[-'][A-Za-zА-Яа-яЁё0-9]+)?", s))


def transcribe_whisper(audio_path: str, language: str, model_size: str):
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_gen, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True
    )
    segments = list(segments_gen)
    transcript = " ".join(s.text.strip() for s in segments)
    words = []
    for s in segments:
        if s.words:
            for w in s.words:
                if w.word is None:
                    continue
                words.append({"word": w.word.strip(), "start": float(w.start), "end": float(w.end)})
    total_dur = float(segments[-1].end) if segments else 0.0
    return transcript.strip(), words, segments, total_dur


def build_pyannote_vad(hf_token: Optional[str] = None):
    token = hf_token or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Hugging Face token is required for pyannote VAD. "
            "Provide --hf_token or set HUGGINGFACE_TOKEN in .env"
        )
    try:
        return Pipeline.from_pretrained("pyannote/voice-activity-detection", token=token)
    except TypeError:
        return Pipeline.from_pretrained("pyannote/voice-activity-detection", use_auth_token=token)


def compute_speech_segments(vad_pipeline, audio_path: str) -> List[Tuple[float, float]]:
    output = vad_pipeline(audio_path)
    timeline = output.get_timeline().support()
    segs = [(float(seg.start), float(seg.end)) for seg in timeline]
    segs = sorted(segs, key=lambda x: x[0])
    return segs


def long_pauses_from_segments(
    speech_segs: List[Tuple[float, float]],
    threshold_sec: float,
    total_duration: float
):
    spoken_time = sum(e - s for s, e in speech_segs)
    overall_time = max(total_duration, (speech_segs[-1][1] if speech_segs else 0.0))
    pauses = []
    for (s1, e1), (s2, e2) in zip(speech_segs, speech_segs[1:]):
        gap = s2 - e1
        if gap >= threshold_sec:
            pauses.append({"start": round(e1, 3), "end": round(s2, 3), "dur": round(gap, 3)})
    return pauses, spoken_time, overall_time


def find_patterns_with_timestamps(words, patterns):
    tokens = [re.sub(r"[^\wа-яё-]+", "", w["word"].lower()) for w in words]
    joined = " ".join(t for t in tokens if t)
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
            start_t = words[start_idx]["start"] if words else 0.0
            end_t = words[end_idx]["end"] if words else start_t
            hits.append({"start": round(float(start_t), 3),
                         "end": round(float(end_t), 3),
                         "text": m.group(0)})
        if cnt:
            results.append({"pattern": pat, "count": cnt, "occurrences": hits})
            total += cnt
    return results, total


def split_script_units(text: str):
    if not text:
        return []
    raw = re.split(r"(?:[\n\r]+|•|- |\u2022|—|–|;|\.)(?:\s+|$)", text)
    units = [u.strip() for u in raw if u and u.strip()]
    units = [u for u in units if word_count(u) >= 3]
    return units


def group_segment_texts(segments, max_seconds=12, max_words=60):
    out, buf_text = [], []
    window_start, window_end = None, None

    for s in segments:
        if window_start is None:
            window_start, window_end = s.start, s.end
        candidate = " ".join(buf_text + [s.text.strip()])
        if (s.end - window_start) <= max_seconds and word_count(candidate) <= max_words:
            buf_text.append(s.text.strip())
            window_end = s.end
        else:
            if buf_text:
                out.append(" ".join(buf_text))
            buf_text = [s.text.strip()]
            window_start, window_end = s.start, s.end

    if buf_text:
        out.append(" ".join(buf_text))
    return out


def compute_coverage(script_text: str, seg_texts: list,
                     threshold: float = COVERAGE_THRESHOLD):
    if not script_text or not seg_texts:
        return None
    units = split_script_units(script_text)
    if not units:
        return {"coverage": None, "missing": [], "matches": []}

    model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
    E_units = model.encode(units, normalize_embeddings=True, convert_to_tensor=True)
    E_segs  = model.encode(seg_texts, normalize_embeddings=True, convert_to_tensor=True)
    sims = util.cos_sim(E_units, E_segs).cpu().numpy()

    matches, missing = [], []
    for i, unit in enumerate(units):
        unit_thr = SHORT_UNIT_THRESHOLD if word_count(unit) <= SHORT_UNIT_WORDS else threshold
        j = int(np.argmax(sims[i]))
        score = float(sims[i][j])
        if score >= unit_thr:
            matches.append({"unit_idx": i, "unit": unit,
                            "seg_idx": j, "seg": seg_texts[j],
                            "similarity": round(score, 3)})
        else:
            missing.append({"unit_idx": i, "unit": unit,
                            "max_similarity": round(score, 3)})

    coverage = round(100.0 * (len(units) - len(missing)) / len(units), 1)
    return {"coverage": coverage, "missing": missing, "matches": matches}


def analyze(audio_path: str,
            script_text: str = "",
            language: str = DEFAULT_LANGUAGE,
            whisper_size: str = DEFAULT_WHISPER_SIZE,
            pause_threshold: float = LONG_PAUSE_SEC,
            hf_token: Optional[str] = None) -> Dict:

    transcript, words, segments, total_dur = transcribe_whisper(audio_path, language, whisper_size)

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

    return {
        "meta": {
            "audio_path": audio_path,
            "language": language,
            "whisper_size": whisper_size,
            "pause_threshold_sec": pause_threshold,
            "coverage_threshold": COVERAGE_THRESHOLD
        },
        "transcript_text": transcript,
        "duration_sec_total": round(float(overall_time or total_dur), 2),
        "duration_sec_spoken": round(float(spoken_time), 2),
        "words_total": n_words,
        "wpm_overall": overall_wpm,
        "wpm_spoken": spoken_wpm,
        "speech_segments": [{"start": round(s, 3), "end": round(e, 3)} for s, e in speech_segs],
        "long_pauses": pauses,
        "filler_words": fillers,
        "filler_count_total": fillers_total,
        "hedge_phrases": hedges,
        "hedge_count_total": hedges_total,
        "script_alignment": coverage
        # "segment_texts_for_alignment": seg_texts
    }


def analyze_file(audio_path: str,
                 script_path: Optional[str] = None,
                 **kwargs) -> Dict:
    script_text = read_text_file(script_path) if script_path else ""
    return analyze(audio_path=audio_path, script_text=script_text, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Path to audio file (wav/mp3/m4a...)")
    parser.add_argument("--script", help="Path to text script (optional)", default="")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="ASR language hint, e.g., ru or en")
    parser.add_argument("--whisper_size", default=DEFAULT_WHISPER_SIZE)
    parser.add_argument("--pause_threshold", type=float, default=LONG_PAUSE_SEC)
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
        hf_token=hf_token
    )
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved results to {args.out}")
    print(f"WPM (spoken/overall): {result['wpm_spoken']} / {result['wpm_overall']}")
    print(f"Fillers: {result['filler_count_total']}, Hedges: {result['hedge_count_total']}")
    if result["script_alignment"]:
        print(f"Coverage: {result['script_alignment']['coverage']}%")


if __name__ == "__main__":
    main()
