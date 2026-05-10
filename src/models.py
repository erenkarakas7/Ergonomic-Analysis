import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

# --- HATA ÇÖZÜMÜ: Veritabanı klasörünün olduğundan emin ol ---
if not os.path.exists("./data"):
    os.makedirs("./data")

# SQLite veritabanı bağlantı adresi
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/ergonomic_data.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# --- 1. İŞÇİLER TABLOSU ---
class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    department = Column(String)

    # Bire-Çok İlişki: Bir işçinin birden fazla oturumu olabilir
    sessions = relationship("Session", back_populates="worker")


# --- 2. İŞ İSTASYONLARI TABLOSU ---
class Workstation(Base):
    __tablename__ = "workstations"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String)
    camera_id = Column(String)  # Hangi kameradan görüntü alındığı

    sessions = relationship("Session", back_populates="workstation")


# --- 3. OTURUMLAR (SESSIONS) TABLOSU ---
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    workstation_id = Column(Integer, ForeignKey("workstations.id"))
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)  # Oturum bitince güncellenecek

    worker = relationship("Worker", back_populates="sessions")
    workstation = relationship("Workstation", back_populates="sessions")
    risk_logs = relationship("RiskLog", back_populates="session")


# --- 4. DETAYLI RİSK KAYITLARI TABLOSU ---
class RiskLog(Base):
    __tablename__ = "risk_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    timestamp = Column(DateTime, default=datetime.now)

    # Yöneticilerin raporlaması için REBA alt skorları
    neck_score = Column(Integer)
    trunk_score = Column(Integer)
    arm_score = Column(Integer)

    final_reba_score = Column(Integer)
    risk_level = Column(String)

    # Acil müdahale gerektiren anları belirlemek için
    is_critical = Column(Integer, default=0)

    session = relationship("Session", back_populates="risk_logs")


# Tabloları veritabanında fiziksel olarak oluştur
Base.metadata.create_all(bind=engine)