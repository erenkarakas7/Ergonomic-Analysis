# ErgonVisio

A desktop application that detects a worker's posture from a camera or video file and calculates an ergonomic risk score using the REBA method. Scores are shown live, logged to a database once per second, and can be reviewed later per workstation or per worker with charts.

I built this with an occupational health and safety (OHS) scenario in mind, but it is not a substitute for an expert assessment. The calculation is a simplified adaptation of REBA (see "Limitations" below).

The interface is in Turkish.

## How it works

1. MediaPipe Pose finds body landmarks in each frame.
2. Angles are calculated from the ear, shoulder, elbow, wrist, hip and index finger points (`reba_analyzer.py`).
3. The angles are converted into neck, trunk, upper arm, lower arm and wrist scores, then combined using the standard REBA Tables A, B and C.
4. The load, coupling, activity and leg values selected by the user at the start of a session are added to the score.
5. The final score is shown live and written to SQLite through FastAPI once per second.

Video processing runs in a separate `QThread` so the interface does not freeze. Log requests are sent from another thread.

## Files

| File | Purpose |
|---|---|
| `app_gui.py` | PyQt5 interface: menus, analysis screen, record management, reporting |
| `main_api.py` | FastAPI service and SQLAlchemy models |
| `vision_module.py` | MediaPipe Pose wrapper (`PoseDetector`) |
| `reba_analyzer.py` | Angle calculation and REBA tables |

Note: the `main()` function in `vision_module.py` is left over from an earlier test flow and is not used by the application.

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy opencv-python mediapipe PyQt5 matplotlib numpy requests
```

Python version I tested with: `3.11`

## Running

Two separate terminals are needed.

```bash
# 1. API
uvicorn main_api:app --port 8001

# 2. Interface
python app_gui.py
```

The API address is hardcoded as `API_URL` (`http://127.0.0.1:8001`) at the top of `app_gui.py` and `vision_module.py`. If you change the port, update it there.

The database (`ergovision_V4.db`) is created automatically on first run. Its location is set by `BASE_DIR` in `main_api.py`; at the moment a `data/` folder is created one directory above the project folder.

## Usage

1. In the **Database Management** menu, add workers and workstations (new names typed when starting a session are also created automatically).
2. In the **Analysis** menu, choose the operator, workstation, start time and physical conditions:
   - Load: 0 / 1 / 2 points
   - Coupling: 0 / 1 / 2 points
   - Leg posture: 1 / 2 points
   - Activity: 1 (static/repetitive) or 0 (dynamic)
3. Choose a camera or an `.mp4` / `.avi` file as the source and press **Start**.
4. During analysis, the REBA score, risk level, neck/trunk/arm/leg scores and a color-coded body diagram update live. Pause and resume are available.
5. When the video ends, a summary is shown: total time, critical time and risk ratio. If critical frames exceed 30%, a "risk threshold exceeded" warning is shown.
6. In the **Reporting** menu, review averages for all workstations or the sessions of a selected worker as charts and tables.

## Risk levels

| REBA score | Level |
|---|---|
| 1 | Negligible |
| 2-3 | Low |
| 4-7 | Medium |
| 8-10 | High |
| 11+ | Very high |

A record is flagged as `is_critical` when the score is 8 or above.

## API

All parameters are currently sent as query strings.

| Method | Path | Description |
|---|---|---|
| POST | `/workers/` | Add a worker |
| GET | `/workers/` | List workers |
| DELETE | `/workers/{worker_id}` | Delete a worker |
| POST | `/workstations/` | Add a workstation |
| GET | `/workstations/` | List workstations |
| DELETE | `/workstations/{ws_id}` | Delete a workstation |
| POST | `/create_session/` | Start a session, returns `session_id` |
| POST | `/log_risk/` | Write one risk record |
| GET | `/reports/all/` | Latest 300 records |
| GET | `/stats/stations/` | Averages per workstation |
| GET | `/worker_sessions/{worker_name}` | Sessions of a worker |
| GET | `/stats/session/{session_id}` | Records of one session |

While FastAPI is running, automatic documentation is available at `http://127.0.0.1:8001/docs`.

## Database

SQLite with SQLAlchemy. Four tables: `workers`, `workstations`, `sessions`, `risk_logs`. A worker and a workstation can each have many sessions, and a session can have many risk records. Deleting a worker or workstation also deletes the sessions and records that belong to it.

## Limitations

- REBA is applied in a simplified form: neck is scored 1-2, trunk 1-4 and upper arm 1-4. Some additional adjustments from standard REBA (side bending, twisting, arm abduction, etc.) are not included.
- The leg score is not calculated from the image; the user selects it manually at the start of a session.
- Only landmarks on the left side of the body are used, so the camera angle should suit that.
- Angles are calculated from 2D coordinates of a single camera, so results are sensitive to camera angle. They are not measurement-device accuracy.
- One session and one camera at a time.
- I have not measured FPS or latency.
- There is no authentication; the API is intended for local use only.

## To do

- Move parameters into Pydantic models and the request body
- Show errors to the user instead of silently ignoring them
- Package with Docker
- Export session data (CSV)
- Two-sided (left/right) analysis

## Author

Eren Karakaş, [@erenkarakas7](https://github.com/erenkarakas7)

REBA method: Hignett, S. & McAtamney, L. (2000). *Rapid Entire Body Assessment (REBA)*. Applied Ergonomics, 31(2), 201-205.
