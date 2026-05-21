import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy import func
from datetime import datetime

# Veritabanı kurulumu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'ergovision_V4.db')}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    department = Column(String)
    sessions = relationship("DbSession", back_populates="worker", cascade="all, delete-orphan")


class Workstation(Base):
    __tablename__ = "workstations"
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String)
    camera_id = Column(String)
    sessions = relationship("DbSession", back_populates="workstation", cascade="all, delete-orphan")


class DbSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    workstation_id = Column(Integer, ForeignKey("workstations.id"))
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)


    load_score = Column(Integer, default=0)
    coupling_score = Column(Integer, default=0)
    activity_score = Column(Integer, default=1)
    legs_score = Column(Integer, default=1)

    worker = relationship("Worker", back_populates="sessions")
    workstation = relationship("Workstation", back_populates="sessions")
    risk_logs = relationship("RiskLog", back_populates="session", cascade="all, delete-orphan")


class RiskLog(Base):
    __tablename__ = "risk_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    location_name = Column(String, default="Bilinmiyor")
    timestamp = Column(DateTime, default=datetime.now)
    neck_score = Column(Integer)
    trunk_score = Column(Integer)
    arm_score = Column(Integer)
    leg_score = Column(Integer, default=1) # Bacak skorunu ekledimm.
    final_reba_score = Column(Integer)
    risk_level = Column(String)
    is_critical = Column(Integer, default=0)
    session = relationship("DbSession", back_populates="risk_logs")


Base.metadata.create_all(bind=engine)

# FastAPI uç noktaları
app = FastAPI(title="Ergonomic Risk Assessment API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_log(log):
    return {
        "id": log.id, "session_id": log.session_id, "location_name": log.location_name,
        "neck_score": log.neck_score, "trunk_score": log.trunk_score,
        "arm_score": log.arm_score, "leg_score": log.leg_score,  # BACAK EKLENDİ
        "final_reba_score": log.final_reba_score, "risk_level": log.risk_level, "is_critical": log.is_critical
    }


@app.get("/")
def read_root(): return {"message": "API ÇALIŞIYOR!"}


@app.post("/workers/")
def create_worker(full_name: str, department: str, db: Session = Depends(get_db)):
    existing = db.query(Worker).filter(Worker.full_name == full_name).first()
    if existing: raise HTTPException(status_code=400, detail="Bu isimde bir personel zaten kayıtlı!")
    new_worker = Worker(full_name=full_name, department=department)
    db.add(new_worker);
    db.commit();
    db.refresh(new_worker)
    return {"message": "Worker added successfully"}


@app.get("/workers/")
def get_workers(db: Session = Depends(get_db)): return db.query(Worker).all()


@app.delete("/workers/{worker_id}")
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker: raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    db.delete(worker);
    db.commit()
    return {"message": "Silindi"}


@app.post("/workstations/")
def create_workstation(location_name: str, camera_id: str = "Bilinmiyor", db: Session = Depends(get_db)):
    existing = db.query(Workstation).filter(Workstation.location_name == location_name).first()
    if existing: raise HTTPException(status_code=400, detail="Bu isimde bir istasyon zaten kayıtlı!")
    new_ws = Workstation(location_name=location_name, camera_id=camera_id)
    db.add(new_ws);
    db.commit();
    db.refresh(new_ws)
    return {"message": "Workstation added successfully"}


@app.get("/workstations/")
def get_workstations(db: Session = Depends(get_db)): return db.query(Workstation).all()


@app.delete("/workstations/{ws_id}")
def delete_workstation(ws_id: int, db: Session = Depends(get_db)):
    ws = db.query(Workstation).filter(Workstation.id == ws_id).first()
    if not ws: raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    db.delete(ws);
    db.commit()
    return {"message": "Silindi"}


@app.post("/create_session/")
def create_session(worker_name: str, location_name: str, start_time_str: str = None,
                   load_score: int = 0, coupling_score: int = 0, activity_score: int = 1, legs_score: int = 1,
                   db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.full_name == worker_name).first()
    if not worker:
        worker = Worker(full_name=worker_name, department="Tanımsız")
        db.add(worker);
        db.commit();
        db.refresh(worker)

    ws = db.query(Workstation).filter(Workstation.location_name == location_name).first()
    if not ws:
        ws = Workstation(location_name=location_name, camera_id="CAM-01")
        db.add(ws);
        db.commit();
        db.refresh(ws)

    final_start_time = datetime.now()
    if start_time_str:
        try:
            parsed_time = datetime.strptime(start_time_str, "%H:%M").time()
            final_start_time = datetime.combine(datetime.now().date(), parsed_time)
        except:
            pass

    new_session = DbSession(worker_id=worker.id, workstation_id=ws.id, start_time=final_start_time,
                            load_score=load_score, coupling_score=coupling_score, activity_score=activity_score,
                            legs_score=legs_score)
    db.add(new_session);
    db.commit();
    db.refresh(new_session)
    return {"session_id": new_session.id}


@app.post("/log_risk/")
def log_risk(session_id: int, neck: int, trunk: int, arm: int, leg: int, final_score: int,
             risk_level: str, location_name: str = "Bilinmiyor", is_critical: int = 0, db: Session = Depends(get_db)):
    new_log = RiskLog(session_id=session_id, location_name=location_name, neck_score=neck,
                      trunk_score=trunk, arm_score=arm, leg_score=leg, final_reba_score=final_score,
                      risk_level=risk_level, is_critical=is_critical)
    db.add(new_log);
    db.commit()
    return {"message": "Logged successfully"}


@app.get("/reports/all/")
def get_all_logs(db: Session = Depends(get_db)):
    logs = db.query(RiskLog).order_by(RiskLog.id.desc()).limit(300).all()
    return [serialize_log(l) for l in logs]


@app.get("/stats/stations/")
def get_station_stats(db: Session = Depends(get_db)):
    stats = db.query(
        RiskLog.location_name, func.avg(RiskLog.final_reba_score).label("avg_reba"),
        func.avg(RiskLog.neck_score).label("avg_neck"), func.avg(RiskLog.trunk_score).label("avg_trunk")
    ).group_by(RiskLog.location_name).all()
    return [{"location_name": s.location_name, "avg_reba": s.avg_reba or 0,
             "avg_neck": s.avg_neck or 0, "avg_trunk": s.avg_trunk or 0} for s in stats]


@app.get("/worker_sessions/{worker_name}")
def get_worker_sessions(worker_name: str, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.full_name == worker_name).first()
    if not worker: return []
    sessions = db.query(DbSession).filter(DbSession.worker_id == worker.id).order_by(DbSession.id.desc()).all()
    result = []
    for s in sessions:
        ws = db.query(Workstation).filter(Workstation.id == s.workstation_id).first()
        loc_name = ws.location_name if ws else "Bilinmiyor"
        st_time = s.start_time.strftime("%d.%m.%Y - %H:%M") if s.start_time else "Bilinmiyor"
        # UI'da göstermek üzere parametreleri de gönderiyoruz
        result.append({
            "id": s.id, "location": loc_name, "start_time": st_time,
            "load": s.load_score, "coupling": s.coupling_score, "activity": s.activity_score, "legs": s.legs_score
        })
    return result


@app.get("/stats/session/{session_id}")
def get_session_stats(session_id: int, db: Session = Depends(get_db)):
    logs = db.query(RiskLog).filter(RiskLog.session_id == session_id).order_by(RiskLog.id.asc()).all()
    return [serialize_log(l) for l in logs]