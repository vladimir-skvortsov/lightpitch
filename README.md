# LightPitch

**LightPitch** is an **AI coach for public speaking**. Upload a pitch (video/audio) or record in the browser, and the system analyzes **speech, eye contact & gestures, text, and slides**. It aggregates metrics into a single score and returns **clear, actionable recommendations**.

**Who it’s for:** founders, PMs/analysts, educators, students, and internal demo speakers.
**Why:** prepare a stronger pitch faster—reduce fillers, improve eye contact and posture, and make slides more readable—with objective progress metrics.

Architecture: **Frontend (React + Vite + Tailwind)**, **Backend (FastAPI)**, and ML pipelines for **audio / video / text / slides**, runnable via **Docker** or locally.

---

## Table of Contents

* [Stack](#stack)
* [Features & Metrics](#features--metrics)
* [Repository Structure](#repository-structure)
* [Requirements](#requirements)
* [Quick Start](#quick-start)
  * [Environment Variables](#environment-variables)
  * [Run with Docker Compose](#run-with-docker-compose)
  * [Run via `run.sh`](#run-via-runsh)
* [API & Frontend](#api--frontend)
* [Pipelines](#pipelines)
* [Pre-commit & Code Style](#pre-commit--code-style)
* [License](#license)
* [Developers](#developers)

---

## Stack

* **Frontend:** React + Vite + TailwindCSS
* **Backend:** FastAPI (Uvicorn)
* **ML / CV / Audio:** OpenCV, MediaPipe (FaceMesh / Hands / Pose), ffmpeg, pyannote.audio (VAD), faster-whisper (ASR), LangChain (NLP helpers)
* **Infra:** Docker, docker compose, Nginx (prod/static)

---

## Features & Metrics

* **Audio:** speech rate, pauses/fillers, fluency, speech share, ASR with timestamps, coverage vs. a reference script.
* **Video:** eye visibility, blink filtering, gaze/eye contact, posture & gestures (openness/activeness).
* **Text:** clarity, structure, tone/style, rewrite suggestions.
* **Slides:** readability, density, visual hierarchy.
* **Overall:** aggregated score + actionable recommendations.

---

## Repository Structure

```
.
├── app/
│   ├── backend/
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── db_models.py
│   │   ├── main.py
│   │   ├── pitches.py
│   │   ├── uploads/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/
│       ├── src/
│       ├── public/
│       ├── dist/
│       └──  package.json
├── models/
│   ├── audio/
│   ├── description_generator/
│   ├── presentation_grader/
│   ├── text_editor/
│   ├── video_grader/
│   ├── utils/
│   └── __init__.py
├── data/
├── nginx/
├── .env
├── .env.example
├── docker-compose.yaml
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
├── run.sh
└── README.md
```

---

## Requirements

* **Docker** 24+ and **docker compose** (or Docker Desktop), or
* **Python** 3.11+ and **Node.js** 18+ for local dev without containers.

---

## Quick Start

### Environment Variables

Copy `.env.example` → `.env` and adjust as needed:

### Run with Docker Compose

```bash
# build and start
docker compose up -d --build

# tail logs (examples)
docker compose logs -f backend
docker compose logs -f frontend

# stop
docker compose down
```

* Backend (FastAPI): `http://localhost:8000` → Swagger at `/docs`
* Frontend: port is defined in `docker-compose.yml`

### Run via `run.sh`

Helper script for a quick dev start:

```bash
# Run both frontend and backend services
./run.sh all

# Run only the backend service
./run.sh backend

# Run only the frontend service
./run.sh frontend

# Show help
./run.sh help
```

---

## API & Frontend

* **FastAPI** — see `app/backend/*.py`. After start, interactive docs are available at `/docs` and `/redoc`.
* **Frontend** — SPA in `app/frontend/src`. In dev, Vite serves the UI on its own port; for prod, use `npm run build` and serve `dist/` (e.g., via Nginx).

---

## Pipelines

**Speech / Audio**

1. Audio normalization (ffmpeg)
2. VAD (pyannote.audio) — speech segment detection
3. ASR (faster-whisper) — transcription with word timestamps
4. Metrics: speech rate, pauses/fillers, fluency, speech share
5. Coverage vs. a provided reference script (optional)

**Vision / Video**

1. Frame extraction (OpenCV)
2. FaceMesh — eye visibility, blink filtering, gaze/eye contact estimation
3. Pose/Hands (MediaPipe) — posture and gesture “openness/activeness”
4. Metric aggregation by timestamps

**Text / Slides**

* Text: clarity, structure, tone/style, rewrite suggestions
* Slides: readability, density, visual hierarchy, recommendations

---

## Models

```
models/
├── audio/                    # speech metrics, VAD/ASR pipeline glue
├── video_grader/             # gaze/contact, posture, gestures
├── presentation_grader/      # slide/image analysis
├── text_editor/              # structure/tone suggestions
├── description_generator/    # description generation
└── utils/
```

---

## Pre-commit & Code Style

Install and run:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

---

## License

See [`LICENSE`](./LICENSE).

---

## Developers

* [Lead — Vladimir Skvortsov](https://github.com/vladimir-skvortsov)
* [ML Engineer — Name Surname](https://github.com/LuckyAm20)
* [ML Engineer — Andrew Afanasev](https://github.com/afafos)
* [ML Engineer — Mary Prohorova](https://github.com/tatar04k)

---
