# ErgonVisio

ErgonVisio is a local-first, production-ready industrial ergonomic risk assessment system. It eliminates the manual overhead of traditional İSG (Occupational Health and Safety) audits by combining computer vision pose estimation with the standardized **Rapid Entire Body Assessment (REBA)** methodology.

The system is decoupled into an asynchronous client-server architecture to handle high-frequency video processing (30 FPS) without UI blocking or frame drops.

---

## Architecture Overview

Traditional vision-based assessment tools suffer from performance degradation when UI rendering, video decoding, coordinate math, and database I/O run on a single thread. ErgonVisio solves this via a decoupled architecture:

1. **Frontend Client (PyQt5):** Captures video/camera streams, processes frames using **Google MediaPipe Pose** (33 3D landmarks), calculates joint angles, and renders a dynamic digital twin vector map.
2. **Backend Server (FastAPI):** Exposes a RESTful API to manage master data (Workers, Workstations) and logs high-frequency risk metrics asynchronously.
3. **Storage (SQLite & SQLAlchemy ORM):** Persists time-series risk logs and task metadata locally within the factory network.

```text
[Camera / Video Stream]
         │
         ▼
 ┌───────────────┐
 │ PyQt5 Client  │ ──(Processes 30 FPS MediaPipe Frames)
 └───────┬───────┘
         │ (Asynchronous HTTP POST /log_risk/)
         ▼
 ┌───────────────┐
 │ FastAPI Core  │
 └───────┬───────┘
         │ (SQLAlchemy ORM)
         ▼
 ┌───────────────┐
 │  SQLite DB    │ ──(Stored locally on-premise)
 └───────────────┘

Core Engineering Features
1. Hybrid Assessment (Human-in-the-Loop)
Pure computer vision models cannot detect environmental variables like load weight or grasp quality. ErgonVisio blends spatial data with administrative inputs:

AI Engine: Automatically extracts neck, trunk, and upper arm deflection angles using spatial vectors.

Expert Inputs: The OHS specialist injects discrete parameters (e.g., Load >10kg, Poor Coupling, Unstable Leg Posture) via the UI session manager. These are combined deterministically using the official REBA matrix tables.

2. On-Premise Data Sovereignty (Edge Computing)
Heavy industrial and defense facilities operate under strict privacy compliance policies (KVKK / GDPR). ErgonVisio requires zero internet connectivity. Videos and telemetry logs never leave the local factory network, mitigating cybersecurity risks associated with third-party cloud SaaS platforms.

3. High-Frequency Risk Telemetry
Dynamic Digital Twin: Re-draws vector joint highlights in real-time, changing node colors (Green/Orange/Red) dynamically based on specific limb risk metrics.

Time-Series Analytics: Generates per-second trend lines and station-based risk distribution charts using Matplotlib integration, identifying micro-movements that cause cumulative Musculoskeletal Disorders (MSDs).

Technology Stack
GUI Framework: PyQt5

Core CV Engine: Google MediaPipe (Pose Solution)

API Backend: FastAPI (Asynchronous Python Web Framework)

ASGI Server: Uvicorn

Database / ORM: SQLite / SQLAlchemy

Data Visualization: Matplotlib / NumPy

HTTP Client: Requests

Getting Started
Prerequisites
Python 3.10 or 3.11

On-premise environment (Windows/Linux/macOS)

Installation
Clone the repository and navigate to the project root:

Bash
git clone [https://github.com/yourusername/Ergonomic-Analysis.git](https://github.com/yourusername/Ergonomic-Analysis.git)
cd Ergonomic-Analysis
Create and activate an isolated virtual environment:

Bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
Install the frozen dependencies:

Bash
pip install -r requirements.txt
Execution
The application must be launched in two parts: the backend API server first, followed by the desktop GUI client.

Start the FastAPI Server:

Bash
uvicorn src.main_api:app --host 127.0.0.1 --port 8001 --reload
Verify the API is live by navigating to http://127.0.0.1:8001/docs in your browser to view the interactive Swagger UI.

Launch the Desktop Application:
Open a separate terminal window (ensure the venv is active) and run:

Bash
python src/app_gui.py
Methodology & Scoring Verification
The algorithm relies strictly on the published Rapid Entire Body Assessment (REBA) empirical tables. The risk scoring criteria are classified dynamically:

Score 1: Negligible Risk

Score 2-3: Low Risk (Change may be needed)

Score 4-7: Medium Risk (Further investigation, change soon)

Score 8-10: High Risk (Investigate and implement change soon)

Score 11+: Very High Risk (Implement change immediately)