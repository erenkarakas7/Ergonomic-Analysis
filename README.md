# ErgonVisio - Industrial Ergonomic Risk Assessment System

A comprehensive real-time ergonomic risk assessment platform utilizing computer vision and REBA (Rapid Entire Body Assessment) analysis to monitor workplace posture and identify occupational health hazards in industrial environments.

## Overview

ErgonVisio is an integrated solution designed for occupational safety and health (OSH) professionals to assess and monitor ergonomic risks in real-time. The system uses pose detection technology to analyze worker posture and applies the standardized REBA methodology to generate quantitative risk scores, enabling data-driven interventions to prevent musculoskeletal disorders.

**Key Capabilities:**
- Real-time pose detection and tracking
- Automated REBA score calculation
- Multi-workstation monitoring
- Historical data analytics and trend analysis
- Worker performance profiles and risk stratification
- Intuitive dashboard with visual risk indicators

## Architecture

### System Components

```
ErgonVisio/
├── app_gui.py              # Desktop application interface (PyQt5)
├── main_api.py             # RESTful API backend (FastAPI)
├── vision_module.py        # Computer vision processing layer
├── reba_analyzer.py        # REBA scoring engine
└── data/
    └── ergovision_V4.db    # SQLite database
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | PyQt5 | Cross-platform GUI with real-time visualization |
| **Backend** | FastAPI | High-performance REST API with async support |
| **Computer Vision** | MediaPipe, OpenCV | Pose detection and landmark tracking |
| **Database** | SQLite + SQLAlchemy | Persistent data storage and ORM |
| **Analysis** | NumPy, Matplotlib | Statistical analysis and visualization |

## Installation

### Prerequisites

- Python 3.8 or higher
- Webcam or video file for input
- 2+ GB RAM recommended
- Windows/macOS/Linux compatible

### Setup Instructions

1. **Clone and navigate to project directory:**
   ```bash
   cd ergovision
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn sqlalchemy opencv-python mediapipe pyqt5 matplotlib numpy requests
   ```

4. **Database initialization** (automatic on first run):
   ```bash
   mkdir -p data
   ```

## Usage

### Starting the System

**Step 1: Launch the API server**
```bash
python main_api.py  # or use: uvicorn main_api:app --host 127.0.0.1 --port 8001 --reload
```

**Step 2: Launch the desktop application**
```bash
python app_gui.py
```

### Workflow

#### 1. System Setup
- Open **PERSONNEL MANAGEMENT** to register workers and workstations
- Configure REBA parameters (load, coupling, activity scores) if required

#### 2. Start Analysis Session
- Click **ANALYSIS** from main menu
- Select video source (webcam or local file)
- Choose worker name and workstation location
- Adjust REBA weighting parameters as needed
- Click **START ANALYSIS**

#### 3. Real-time Monitoring
- Live pose detection with skeletal overlay
- Real-time REBA score with color-coded risk levels
- Dynamic body model showing risk status per body segment
- Continuous data logging to database at 1-second intervals

#### 4. Review Results
- Access **REPORTING** menu after analysis
- View facility-wide statistics and trends
- Analyze individual worker performance profiles
- Export session data for further investigation

## API Endpoints

### Worker Management
```
POST   /workers/              - Register new worker
GET    /workers/              - List all workers
DELETE /workers/{worker_id}   - Remove worker record
```

### Workstation Management
```
POST   /workstations/         - Add new workstation/location
GET    /workstations/         - List all workstations
DELETE /workstations/{ws_id}  - Remove workstation
```

### Session Control
```
POST   /create_session/       - Initialize analysis session
GET    /worker_sessions/{name} - Retrieve worker's session history
```

### Data Logging
```
POST   /log_risk/             - Record frame-level REBA assessment
GET    /reports/all/          - Retrieve recent logs (300 limit)
GET    /stats/session/{id}    - Session-specific statistics
GET    /stats/stations/       - Facility-level aggregated statistics
```

## REBA Scoring System

### Overview
REBA (Rapid Entire Body Assessment) is a validated ergonomic assessment method that evaluates postural risk using a systematic scoring matrix. The system calculates scores based on:

- **Trunk posture** (flexion, extension, lateral bending)
- **Neck posture** (flexion, extension, rotation)
- **Leg position** (foot placement, weight distribution)
- **Upper arm position** (abduction, elevation)
- **Lower arm position** (deviation from midline)
- **Wrist posture** (deviation, rotation)

### Risk Classification
| REBA Score | Risk Level | Action Required |
|-----------|-----------|-----------------|
| 1 | Negligible | No action necessary |
| 2-3 | Low | Routine monitoring |
| 4-7 | Medium | Intervention may be required |
| 8-10 | High | Immediate intervention needed |
| 11+ | Very High | Emergency intervention |

The system automatically assigns color indicators:
- **Green** (#00C853): Acceptable posture
- **Orange** (#FF9800): Moderate risk
- **Red** (#D32F2F): High-risk situation

## Data Logging and Database Schema

### RiskLog Table Structure
```
RiskLog:
  - id: Unique identifier
  - session_id: Reference to analysis session
  - timestamp: Assessment timestamp
  - location_name: Workstation identifier
  - neck_score: Neck posture component (1-3)
  - trunk_score: Trunk posture component (1-5)
  - arm_score: Upper arm component (1-6)
  - leg_score: Leg component (1-4)
  - final_reba_score: Composite REBA score (1-15)
  - risk_level: Categorical risk assessment
  - is_critical: Flag for high-risk events (score ≥8)
```

Data is logged once per second during active analysis to balance temporal resolution with system performance.

## Configuration

### REBA Parameters
Modifiable weighting factors in the setup interface:

- **Load Score** (0-3): Material handling weight and frequency adjustment
- **Coupling Score** (0-2): Grip quality and hand coupling classification  
- **Activity Score** (0-1): Repetitive or dynamic movement factor
- **Leg Score** (1-4): Base leg stability component

### System Parameters
Edit in `app_gui.py`:
```python
API_URL = "http://127.0.0.1:8001"    # API server address
```

## Performance Specifications

- **Pose Detection**: ~30 FPS on standard hardware
- **REBA Calculation**: <10 ms per frame
- **Database Queries**: Optimized with indexing on session_id
- **Concurrent Users**: Single-instance; enterprise scaling via load balancing

## Troubleshooting

### Common Issues

**Issue**: "API connection refused"
- Solution: Ensure FastAPI server is running on port 8001
  ```bash
  python -m uvicorn main_api:app --port 8001
  ```

**Issue**: Pose detection not working
- Solution: Check webcam permissions and camera connectivity
- Verify MediaPipe installation: `python -c "import mediapipe; print(mediapipe.__version__)"`

**Issue**: Database locked error
- Solution: Close all instances of the application and delete `.db-journal` file in `data/` folder

**Issue**: Low FPS performance
- Solution: Reduce model complexity in `vision_module.py`:
  ```python
  model_complexity=0  # 0=lite, 1=full
  ```

## Data Privacy and Compliance

- All data stored locally in SQLite database
- No cloud transmission by default
- GDPR-compliant with worker data retention policies
- Database encryption recommended for sensitive environments

## Limitations and Future Enhancements

### Current Limitations
- Single camera input per session
- Requires frontal or semi-frontal pose visibility
- Database performance limits ~100K+ records
- No multi-user concurrent analysis

### Planned Features
- Multi-camera support with trajectory tracking
- Machine learning-based anomaly detection
- Predictive risk alerts and intervention recommendations
- Integration with IoT sensors (pressure, temperature)
- Web-based dashboard for remote monitoring
- REST API rate limiting and authentication

## Contributing

Contributions are welcome. Please ensure:
- Code follows PEP 8 style guidelines
- New features include updated documentation
- Database schema changes are migration-compatible
- Testing performed on edge cases

## License

This project is developed for occupational health and safety applications. Contact the development team for licensing information.

## Support and Documentation

For technical support or questions regarding REBA methodology:
- REBA Assessment Guide: Standard occupational health documentation
- MediaPipe Pose: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
- FastAPI Documentation: https://fastapi.tiangolo.com/

## Authors and Acknowledgments

Developed as a specialized ergonomic assessment solution for industrial workplace monitoring and occupational safety compliance.

---
