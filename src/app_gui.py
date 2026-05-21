import sys
import cv2
import time
import requests
import numpy as np
import threading
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QDialog,
                             QLineEdit, QComboBox, QFormLayout, QMessageBox,
                             QFrame, QGroupBox, QSpacerItem, QSizePolicy, QFileDialog,
                             QTimeEdit, QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget)
from PyQt5.QtCore import Qt, QTime, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QImage, QPixmap, QPainter, QColor, QPen, QBrush

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from vision_module import PoseDetector
from reba_analyzer import RebaAnalyzer

# Performans ve bağlantı ayarları
API_URL = "http://127.0.0.1:8001"
os.environ['NO_PROXY'] = '127.0.0.1,localhost'
REQ = requests.Session()
REQ.trust_env = False

INDUSTRIAL_STYLE = """
    QMainWindow, QDialog, QWidget { background-color: #121212; color: #E0E0E0; font-family: 'Segoe UI', Arial, sans-serif; }
    QLabel { color: #E0E0E0; }
    QPushButton { background-color: #1F1F1F; border: 1px solid #333333; border-radius: 3px; padding: 10px; font-weight: bold; color: #FFFFFF; letter-spacing: 0.5px; text-transform: uppercase; }
    QPushButton:hover { background-color: #007ACC; border: 1px solid #00A8E8; }
    QPushButton:disabled { background-color: #1A1A1A; color: #555555; border: 1px solid #222222; }
    QPushButton#BackButton { background-color: #2D2D30; border-left: 4px solid #007ACC; border-radius: 0px; }
    QPushButton#BackButton:hover { background-color: #3E3E42; }
    QLineEdit, QComboBox, QTimeEdit { background-color: #1E1E1E; border: 1px solid #444444; border-radius: 2px; padding: 8px; color: #FFFFFF; font-size: 14px; selection-background-color: #007ACC; }
    QLineEdit:focus, QComboBox:focus, QTimeEdit:focus { border: 1px solid #00A8E8; }
    QGroupBox { border: 1px solid #333333; border-radius: 2px; margin-top: 25px; padding-top: 15px; font-weight: bold; color: #00A8E8; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 15px; padding: 0 8px; }
    QTableWidget { background-color: #1A1A1A; color: #D0D0D0; gridline-color: #333333; border: 1px solid #333333; border-radius: 0px; font-size: 14px; selection-background-color: #007ACC; }
    QHeaderView::section { background-color: #252526; color: #00A8E8; font-weight: bold; padding: 10px; border: none; border-right: 1px solid #333333; border-bottom: 1px solid #333333; text-transform: uppercase; font-size: 12px; }
"""


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#121212')
        self.axes = fig.add_subplot(111)
        self.axes.set_facecolor('#1A1A1A')
        super().__init__(fig)


# Dinamik vücut risk şeması
class BodyModelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 240)
        # Varsayılan (Bekleme) Renkler
        self.neck_color = QColor(100, 100, 100)
        self.trunk_color = QColor(100, 100, 100)
        self.arm_color = QColor(100, 100, 100)
        self.leg_color = QColor(100, 100, 100)

    def update_colors(self, neck, trunk, arm, leg):
        def get_color(score):
            if score <= 1: return QColor(0, 200, 0)       # Yeşil
            elif score == 2: return QColor(255, 165, 0)   # Turuncu
            else: return QColor(211, 47, 47)              # Kırmızı

        self.neck_color = get_color(neck)
        self.trunk_color = get_color(trunk)
        self.arm_color = get_color(arm)
        self.leg_color = get_color(leg)
        # Şemayı yeniden çizdir
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() // 2

        # 1. Anatomik Çizgiler (İskelet Formu)
        pen = QPen(QColor(80, 80, 80))
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Kafa, Omurga, Kollar ve Bacaklar Çizimi
        painter.drawEllipse(cx - 15, 10, 30, 30) # Kafa
        painter.drawLine(cx, 40, cx, 130)        # Omurga
        painter.drawLine(cx, 50, cx - 35, 100)   # Sol Kol
        painter.drawLine(cx, 50, cx + 35, 100)   # Sağ Kol
        painter.drawLine(cx, 130, cx - 25, 210)  # Sol Bacak
        painter.drawLine(cx, 130, cx + 25, 210)  # Sağ Bacak

        # 2. Risk İşaretçileri (Renkli Daireler)
        painter.setPen(Qt.NoPen)

        # Boyun Noktası
        painter.setBrush(QBrush(self.neck_color))
        painter.drawEllipse(cx - 7, 35, 14, 14)

        # Gövde Noktası
        painter.setBrush(QBrush(self.trunk_color))
        painter.drawEllipse(cx - 10, 80, 20, 20)

        # Kollar (İki kola da aynı risk rengi veriliyor)
        painter.setBrush(QBrush(self.arm_color))
        painter.drawEllipse(cx - 40, 95, 14, 14)
        painter.drawEllipse(cx + 26, 95, 14, 14)

        # Bacaklar
        painter.setBrush(QBrush(self.leg_color))
        painter.drawEllipse(cx - 30, 160, 14, 14)
        painter.drawEllipse(cx + 16, 160, 14, 14)


class VideoThread(QThread):

    change_pixmap_signal = pyqtSignal(QImage)
    update_stats_signal = pyqtSignal(int, str, str, int, int, int, int)
    finished_signal = pyqtSignal(dict)

    def __init__(self, source_path, session_id, location_name="Bilinmiyor", reba_params=(0, 0, 1, 1)):
        super().__init__()
        self._run_flag = True
        self._pause_flag = False
        self.source_path = source_path
        self.session_id = session_id
        self.location_name = location_name
        self.detector = PoseDetector()
        self.analyzer = RebaAnalyzer()
        self.last_log_time = time.time()
        self.stats = {"total_frames": 0, "high_risk_frames": 0, "fps": 30.0}
        self.analyzer.set_parameters(*reba_params)
    # Ana çalıştırma fonksiyonu
    def run(self):
        cap = cv2.VideoCapture(self.source_path)
        if cap.get(cv2.CAP_PROP_FPS) > 0: self.stats["fps"] = cap.get(cv2.CAP_PROP_FPS)
        while self._run_flag:
            if self._pause_flag: self.msleep(100); continue
            ret, frame = cap.read()
            if not ret: self.finished_signal.emit(self.stats); break
            self.stats["total_frames"] += 1
            frame = self.detector.find_pose(frame, draw=True)
            landmarks = self.detector.get_landmarks()
            reba_score, risk_text, risk_color_hex = 0, "VERİ BEKLENİYOR...", "#555555"
            neck_sc = trunk_sc = arm_sc = leg_sc = 0

            if len(landmarks) != 0:
                ear, shoulder, elbow, wrist, hip, index = [landmarks[i][1:3] for i in [7, 11, 13, 15, 23, 19]]
                reba_score, risk_text, risk_color_bgr = self.analyzer.calculate_final_reba(
                    (ear, shoulder, elbow, wrist, hip, index))

                neck_sc = self.analyzer.get_neck_score(ear, shoulder)
                trunk_sc = self.analyzer.get_trunk_score(shoulder, hip)
                arm_sc = self.analyzer.get_upper_arm_score(shoulder, elbow)
                leg_sc = self.analyzer.get_legs_score()  # Bacağı analizörden çek

                if reba_score >= 8:
                    risk_color_hex = "#D32F2F"; self.stats["high_risk_frames"] += 1
                elif reba_score >= 4:
                    risk_color_hex = "#FF9800"
                else:
                    risk_color_hex = "#00C853"

                if time.time() - self.last_log_time >= 1.0:
                    payload = {"session_id": self.session_id, "location_name": self.location_name, "neck": neck_sc,
                               "trunk": trunk_sc, "arm": arm_sc, "leg": leg_sc, "final_score": reba_score,
                               "risk_level": risk_text, "is_critical": (1 if reba_score >= 8 else 0)}

                    def send_log(data):
                        try:
                            REQ.post(f"{API_URL}/log_risk/", params=data, timeout=3)
                        except:
                            pass

                    threading.Thread(target=send_log, args=(payload,), daemon=True).start()
                    self.last_log_time = time.time()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.shape[1] * 3, QImage.Format_RGB888)
            self.change_pixmap_signal.emit(img.scaled(900, 700, Qt.KeepAspectRatio))
            self.update_stats_signal.emit(reba_score, risk_text.upper(), risk_color_hex, neck_sc, trunk_sc, arm_sc,
                                          leg_sc)
        cap.release()

    def stop(self):
        self._run_flag = False; self.wait()

    def pause(self):
        self._pause_flag = True

    def resume(self):
        self._pause_flag = False


class AnalysisWidget(QWidget):
    def __init__(self, main_window, worker, location, s_type, s_path, s_id, params):
        super().__init__()
        self.main_window = main_window
        self.s_path, self.s_id = s_path, s_id
        self.location_name = location
        self.reba_params = params
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        v_panel = QVBoxLayout()
        self.video_lbl = QLabel("SİSTEM HAZIR. BAŞLATILMASI BEKLENİYOR.")
        self.video_lbl.setAlignment(Qt.AlignCenter)
        self.video_lbl.setStyleSheet(
            "background-color: #0A0A0A; border: 1px solid #333333; color: #555555; font-size: 20px; letter-spacing: 1px;")
        v_panel.addWidget(self.video_lbl)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("SİSTEMİ BAŞLAT")
        self.btn_start.setStyleSheet("background-color: #007ACC; color: #FFFFFF; font-size: 15px; padding: 15px;")
        self.btn_start.clicked.connect(self.start_ai)
        self.btn_resume = QPushButton("DEVAM ET")
        self.btn_resume.setEnabled(False)
        self.btn_resume.clicked.connect(self.resume)
        self.btn_pause = QPushButton("DURAKLAT")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_stop = QPushButton("SİSTEMİ DURDUR")
        self.btn_stop.setStyleSheet("background-color: #D32F2F; color: #FFFFFF; font-size: 15px; padding: 15px;")
        self.btn_stop.clicked.connect(self.stop_and_go_home)
        for b in [self.btn_start, self.btn_resume, self.btn_pause, self.btn_stop]: btns.addWidget(b)
        v_panel.addLayout(btns)
        layout.addLayout(v_panel, 7)

        s_panel = QVBoxLayout()
        info = QGroupBox("OTURUM PARAMETRELERİ")
        il = QVBoxLayout()
        il.addWidget(QLabel(f"OPERATÖR: <b>{worker.upper()}</b>"))
        il.addWidget(QLabel(f"İSTASYON: <b>{location.upper()}</b>"))
        il.addWidget(QLabel(f"VERİ KAYNAĞI: <b>{s_type.upper()}</b>"))
        phys_params = f"Yük: {params[0]}p | Kavrama: {params[1]}p | Akt: {params[2]}p | Bacak: {params[3]}p"
        il.addWidget(QLabel(f"FİZİKSEL ŞARTLAR: <b style='color:#00A8E8;'>{phys_params}</b>"))
        info.setLayout(il)
        s_panel.addWidget(info)

        # Skor ve vuvut şşeması yan yana
        live = QGroupBox("GERÇEK ZAMANLI RİSK İZLEME")
        live_layout = QHBoxLayout()

        # Sol Taraf: REBA Skor Sayıları
        score_layout = QVBoxLayout()
        score_layout.setAlignment(Qt.AlignCenter)
        self.lbl_score = QLabel("-")
        self.lbl_score.setStyleSheet("font-size: 60px; color: #555555; font-family: 'Consolas', monospace;")
        self.lbl_score.setAlignment(Qt.AlignCenter)
        self.lbl_risk = QLabel("BEKLEMEDE")
        self.lbl_risk.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(QLabel("REBA SKORU", alignment=Qt.AlignCenter))
        score_layout.addWidget(self.lbl_score)
        score_layout.addWidget(self.lbl_risk)
        live_layout.addLayout(score_layout)

        # Sağ Taraf: Vücut Risk Şeması
        self.body_model = BodyModelWidget()
        live_layout.addWidget(self.body_model, alignment=Qt.AlignCenter)

        live.setLayout(live_layout)
        s_panel.addWidget(live)
        # -----------------------------------------------------

        warn = QGroupBox("SİSTEM DURUMU")
        wl = QVBoxLayout()
        self.lbl_warn = QLabel("Sistem komut bekliyor...")
        self.lbl_warn.setStyleSheet("font-size: 14px; color: #888888;")
        self.lbl_warn.setWordWrap(True)
        wl.addWidget(self.lbl_warn)


        self.lbl_details = QLabel("BOYUN: -  |  GÖVDE: -  |  KOL: -  |  BACAK: -")
        self.lbl_details.setStyleSheet("font-size: 14px; color: #00A8E8; font-weight: bold; margin-top: 10px;")
        wl.addWidget(self.lbl_details)

        warn.setLayout(wl)
        s_panel.addWidget(warn)

        self.summary_box = QGroupBox("ANALİZ SONUCU")
        sum_l = QFormLayout()
        self.lbl_sum_total = QLabel("-")
        self.lbl_sum_safe = QLabel("-")
        self.lbl_sum_risk = QLabel("-")
        self.lbl_sum_ratio = QLabel("-")
        self.lbl_sum_status = QLabel("-")
        for lbl in [self.lbl_sum_total, self.lbl_sum_safe, self.lbl_sum_risk, self.lbl_sum_ratio]: lbl.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #E0E0E0;")
        sum_l.addRow(QLabel("Toplam Süre:"), self.lbl_sum_total)
        sum_l.addRow(QLabel("Güvenli Süre:"), self.lbl_sum_safe)
        sum_l.addRow(QLabel("Kritik Süre:"), self.lbl_sum_risk)
        sum_l.addRow(QLabel("Risk Oranı:"), self.lbl_sum_ratio)
        sum_l.addRow(QLabel("Nihai Durum:"), self.lbl_sum_status)
        self.summary_box.setLayout(sum_l)
        self.summary_box.hide()
        s_panel.addWidget(self.summary_box)

        s_panel.addStretch()
        layout.addLayout(s_panel, 3)

    def start_ai(self):
        self.btn_start.hide()
        self.btn_resume.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.thread = VideoThread(self.s_path, self.s_id, self.location_name, self.reba_params)
        self.thread.change_pixmap_signal.connect(lambda img: self.video_lbl.setPixmap(QPixmap.fromImage(img)))
        self.thread.update_stats_signal.connect(self.update_ui)
        self.thread.finished_signal.connect(self.show_summary)
        self.thread.start()

    def update_ui(self, s, t, c, neck, trunk, arm, leg):
        self.lbl_score.setText(str(s))
        self.lbl_score.setStyleSheet(
            f"font-size: 80px; font-weight: bold; color: {c}; font-family: 'Consolas', monospace;")
        self.lbl_risk.setText(t)
        self.lbl_risk.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {c};")
        self.lbl_warn.setText("Kritik Risk Tespit Edildi." if s >= 8 else "Risk sınırları normal.")
        self.lbl_warn.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {'#D32F2F' if s >= 8 else '#00C853'};")
        if s > 0:
            self.lbl_details.setText(f"BOYUN: {neck}  |  GÖVDE: {trunk}  |  KOL: {arm}  |  BACAK: {leg}")
            self.body_model.update_colors(neck, trunk, arm, leg) # VÜCUT ŞEMASINA VERİLERİ GÖNDER

    def show_summary(self, stats):
        if hasattr(self, 'thread'): self.thread.stop()
        total_f = stats.get("total_frames", 0)
        risk_f = stats.get("high_risk_frames", 0)
        fps = stats.get("fps", 30.0)
        t_sec = total_f / fps if fps > 0 else 0
        r_sec = risk_f / fps if fps > 0 else 0
        s_sec = t_sec - r_sec
        r_percent = (risk_f / total_f * 100) if total_f > 0 else 0
        self.lbl_sum_total.setText(f"{t_sec:.1f} sn")
        self.lbl_sum_safe.setText(f"<span style='color:#00C853;'>{s_sec:.1f} sn</span>")
        self.lbl_sum_risk.setText(f"<span style='color:#D32F2F;'>{r_sec:.1f} sn</span>")
        self.lbl_sum_ratio.setText(f"%{r_percent:.1f}")
        if r_percent > 30:
            self.lbl_sum_status.setText(
                "<span style='color:#D32F2F; font-weight:bold;'>DİKKAT: RİSK EŞİĞİ AŞILDI!</span>")
            self.summary_box.setStyleSheet(
                "QGroupBox { border: 1px solid #D32F2F; color: #D32F2F; font-size: 14px; font-weight: bold; margin-top: 25px; padding-top: 15px; }")
        else:
            self.lbl_sum_status.setText(
                "<span style='color:#00C853; font-weight:bold;'>KABUL EDİLEBİLİR SEVİYE</span>")
            self.summary_box.setStyleSheet(
                "QGroupBox { border: 1px solid #00C853; color: #00C853; font-size: 14px; font-weight: bold; margin-top: 25px; padding-top: 15px; }")
        self.summary_box.show()
        self.btn_resume.hide()
        self.btn_pause.hide()
        self.btn_start.hide()
        self.btn_stop.setText("ANA MENÜYE DÖN")
        self.btn_stop.setStyleSheet("background-color: #007ACC; color: #FFFFFF; font-size: 15px; padding: 15px;")

    def pause(self):
        self.thread.pause()

    def resume(self):
        self.thread.resume()

    def stop_and_go_home(self):
        if hasattr(self, 'thread') and self.thread.isRunning(): self.thread.stop()
        self.main_window.go_home()


class SetupAnalysisWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        l = QVBoxLayout(self)
        l.setContentsMargins(40, 30, 40, 40)
        top = QHBoxLayout()
        btn_back = QPushButton("ANA MENÜYE DÖN")
        btn_back.setObjectName("BackButton")
        btn_back.setFixedSize(180, 45)
        btn_back.clicked.connect(self.main_window.go_home)
        top.addWidget(btn_back)
        top.addStretch()
        l.addLayout(top)
        l.addStretch()
        center_h = QHBoxLayout()
        center_h.addStretch()
        form_box = QGroupBox("YENİ OTURUM PARAMETRELERİ")
        form_box.setFixedWidth(600)
        f_layout = QVBoxLayout(form_box)
        f_layout.setContentsMargins(30, 40, 30, 40)
        f_layout.setSpacing(20)
        f = QFormLayout()

        self.cb_w = QComboBox()
        self.cb_w.setEditable(True)
        self.cb_w.setFixedHeight(40)
        self.cb_l = QComboBox()
        self.cb_l.setEditable(True)
        self.cb_l.setFixedHeight(40)
        self.te_time = QTimeEdit()
        self.te_time.setTime(QTime.currentTime())
        self.te_time.setFixedHeight(40)

        self.cb_load = QComboBox()
        self.cb_load.addItems(["< 5 kg (0 Puan)", "5 - 10 kg (1 Puan)", "> 10 kg (2 Puan)"])
        self.cb_load.setFixedHeight(40)
        self.cb_coupling = QComboBox()
        self.cb_coupling.addItems(
            ["İyi - Tam Kavrama (0 Puan)", "Orta - Kısmi Kavrama (1 Puan)", "Kötü - Güvensiz Kavrama (2 Puan)"])
        self.cb_coupling.setFixedHeight(40)
        self.cb_activity = QComboBox()
        self.cb_activity.addItems(["Statik / Tekrarlayan İş (1 Puan)", "Dinamik / Hareketli (0 Puan)"])
        self.cb_activity.setFixedHeight(40)
        self.cb_legs = QComboBox()
        self.cb_legs.addItems(["Dengeli Ayakta / Oturarak (1 Puan)", "Dengesiz / Tek Bacak (2 Puan)"])
        self.cb_legs.setFixedHeight(40)

        self.cb_s = QComboBox()
        self.cb_s.addItems(["Kamera Cihazı", "Yerel Video Dosyası"])
        self.cb_s.setFixedHeight(40)
        self.btn_f = QPushButton("DOSYA SEÇ")
        self.btn_f.hide()
        self.btn_f.setFixedHeight(40)
        self.btn_f.clicked.connect(self.get_file)
        self.f_path = ""
        self.cb_s.currentIndexChanged.connect(lambda i: self.btn_f.setVisible(i == 1))

        f.addRow(QLabel("Operatör Seçimi:"), self.cb_w)
        f.addRow(QLabel("İstasyon Seçimi:"), self.cb_l)
        f.addRow(QLabel("Başlangıç Saati:"), self.te_time)
        f.addRow(QLabel(""), QLabel(""))
        f.addRow(QLabel("Yük Ağırlığı:"), self.cb_load)
        f.addRow(QLabel("Kavrama Kalitesi:"), self.cb_coupling)
        f.addRow(QLabel("Bacak Duruşu:"), self.cb_legs)
        f.addRow(QLabel("Aktivite Tipi:"), self.cb_activity)
        f.addRow(QLabel(""), QLabel(""))
        f.addRow(QLabel("Veri Kaynağı:"), self.cb_s)
        f.addRow("", self.btn_f)
        f_layout.addLayout(f)

        btn = QPushButton("Analizi Hazırla")
        btn.setStyleSheet(
            "background-color: #007ACC; color: #FFFFFF; font-size: 16px; padding: 15px; margin-top: 15px;")
        btn.clicked.connect(self.go)
        f_layout.addWidget(btn)
        center_h.addWidget(form_box)
        center_h.addStretch()
        l.addLayout(center_h)
        l.addStretch()

    def get_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Video Seç", "", "Video (*.mp4 *.avi)")
        if p: self.f_path = p; self.btn_f.setText(p.split('/')[-1])

    def load_api(self):
        self.cb_w.clear()
        self.cb_l.clear()
        try:
            ws = REQ.get(f"{API_URL}/workers/", timeout=5).json()
            ls = REQ.get(f"{API_URL}/workstations/", timeout=5).json()
            self.cb_w.addItems([x["full_name"] for x in ws])
            self.cb_l.addItems([x["location_name"] for x in ls])
        except Exception as e:
            pass

    def go(self):
        wn, ln = self.cb_w.currentText().strip(), self.cb_l.currentText().strip()
        st_time = self.te_time.time().toString("HH:mm")
        if not wn or not ln:
            QMessageBox.warning(self, "Uyarı", "Lütfen Operatör ve İstasyon seçiniz.")
            return

        load_v = self.cb_load.currentIndex()
        coup_v = self.cb_coupling.currentIndex()
        act_v = 1 if self.cb_activity.currentIndex() == 0 else 0
        leg_v = 1 if self.cb_legs.currentIndex() == 0 else 2

        try:
            params = {
                "worker_name": wn, "location_name": ln, "start_time_str": st_time,
                "load_score": load_v, "coupling_score": coup_v, "activity_score": act_v, "legs_score": leg_v
            }
            res = REQ.post(f"{API_URL}/create_session/", params=params, timeout=5)
            sid = res.json().get("session_id", 999) if res.status_code == 200 else 999
        except Exception as e:
            QMessageBox.critical(self, "Bağlantı Hatası", f"API'ye ulaşılamıyor. Hata: {e}")
            return

        data = {
            "w": wn, "l": ln, "t": self.cb_s.currentText(),
            "p": (0 if self.cb_s.currentIndex() == 0 else self.f_path),
            "id": sid,
            "params": (load_v, coup_v, act_v, leg_v)
        }
        self.main_window.start_live_analysis(data)


class AddWorkerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YENİ PERSONEL")
        self.setFixedSize(350, 200)
        l = QFormLayout(self)
        self.w_name = QLineEdit()
        self.w_dept = QLineEdit()
        l.addRow("Ad Soyad:", self.w_name)
        l.addRow("Departman:", self.w_dept)
        btn = QPushButton("SİSTEME KAYDET")
        btn.setStyleSheet("background-color: #007ACC; color: #FFFFFF; padding: 10px; margin-top: 20px;")
        btn.clicked.connect(self.save)
        l.addRow(btn)

    def save(self):
        name = self.w_name.text().strip()
        dept = self.w_dept.text().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Personel adı boş bırakılamaz!")
            return
        try:
            res = REQ.post(f"{API_URL}/workers/",
                           params={"full_name": name, "department": dept if dept else "Tanımsız"}, timeout=5)
            if res.status_code == 200:
                self.accept()
            elif res.status_code == 400:
                QMessageBox.warning(self, "Çift Kayıt", res.json().get("detail", "Bu kayıt zaten mevcut!"))
            else:
                QMessageBox.warning(self, "Hata", "Kayıt Başarısız: " + res.text)
        except Exception as e:
            QMessageBox.critical(self, "Bağlantı Hatası", f"API Çöktü: {e}")


class AddLocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YENİ İSTASYON")
        self.setFixedSize(350, 200)
        l = QFormLayout(self)
        self.l_name = QLineEdit()
        self.l_cam = QLineEdit()
        l.addRow("İstasyon Adı:", self.l_name)
        l.addRow("Kamera ID:", self.l_cam)
        btn = QPushButton("SİSTEME KAYDET")
        btn.setStyleSheet("background-color: #007ACC; color: #FFFFFF; padding: 10px; margin-top: 20px;")
        btn.clicked.connect(self.save)
        l.addRow(btn)

    def save(self):
        loc = self.l_name.text().strip()
        cam = self.l_cam.text().strip()
        if not loc:
            QMessageBox.warning(self, "Uyarı", "İstasyon adı boş bırakılamaz!")
            return
        try:
            res = REQ.post(f"{API_URL}/workstations/",
                           params={"location_name": loc, "camera_id": cam if cam else "Bilinmiyor"}, timeout=5)
            if res.status_code == 200:
                self.accept()
            elif res.status_code == 400:
                QMessageBox.warning(self, "Çift Kayıt", res.json().get("detail", "Bu kayıt zaten mevcut!"))
            else:
                QMessageBox.warning(self, "Hata", "Kayıt Başarısız: " + res.text)
        except Exception as e:
            QMessageBox.critical(self, "Bağlantı Hatası", f"API Çöktü: {e}")


class ListWidget(QWidget):
    def __init__(self, title, columns, keys, endpoint, AddDialogClass, main_window, back_target):
        super().__init__()
        self.main_window = main_window
        self.back_target = back_target
        self.endpoint = endpoint
        self.AddDialogClass = AddDialogClass
        self.keys = keys
        l = QVBoxLayout(self)
        l.setContentsMargins(40, 30, 40, 40)
        top = QHBoxLayout()
        btn_back = QPushButton("GERİ DÖN")
        btn_back.setObjectName("BackButton")
        btn_back.setFixedSize(150, 45)
        btn_back.clicked.connect(lambda: self.main_window.stack.setCurrentWidget(self.back_target))
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A8E8; margin-left: 20px;")
        top.addWidget(btn_back)
        top.addWidget(lbl_title)
        top.addStretch()
        l.addLayout(top)
        l.addSpacing(20)
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        l.addWidget(self.table)
        btns = QHBoxLayout()
        btn_add = QPushButton("YENİ KAYIT EKLE")
        btn_add.setStyleSheet("background-color: #1F1F1F; color: #FFFFFF; font-size: 14px; padding: 12px;")
        btn_add.clicked.connect(self.add_new)
        btn_del = QPushButton("SEÇİLİ KAYDI SİL")
        btn_del.setStyleSheet(
            "background-color: #D32F2F; color: #FFFFFF; font-size: 14px; padding: 12px; border: none;")
        btn_del.clicked.connect(self.delete_item)
        btn_ref = QPushButton("VERİLERİ YENİLE")
        btn_ref.setStyleSheet("font-size: 14px; padding: 12px;")
        btn_ref.clicked.connect(self.load_data)
        btns.addWidget(btn_add)
        btns.addWidget(btn_del)
        btns.addWidget(btn_ref)
        l.addLayout(btns)

    def load_data(self):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        try:
            data = REQ.get(f"{API_URL}/{self.endpoint}/", timeout=5).json()
            for row, item in enumerate(data):
                self.table.insertRow(row)
                for col, key in enumerate(self.keys):
                    self.table.setItem(row, col, QTableWidgetItem(str(item.get(key, ""))))
        except:
            pass
        self.table.setUpdatesEnabled(True)

    def add_new(self):
        dialog = self.AddDialogClass(self)
        if dialog.exec_() == QDialog.Accepted: self.load_data()

    def delete_item(self):
        row = self.table.currentRow()
        if row < 0: QMessageBox.warning(self, "Uyarı", "İşlem yapılacak satırı seçiniz."); return
        item_id = self.table.item(row, 0).text()
        if QMessageBox.question(self, 'Onay', f"Seçili kayıt (ID: {item_id}) silinecek. Onaylıyor musunuz?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                res = REQ.delete(f"{API_URL}/{self.endpoint}/{item_id}", timeout=5)
                if res.status_code == 200:
                    self.load_data()
                    QMessageBox.information(self, "Başarılı", "Kayıt başarıyla silindi.")
                else:
                    QMessageBox.warning(self, "Hata", f"Silinemedi! Hata Kodu: {res.status_code}")
            except Exception as e:
                QMessageBox.critical(self, "Bağlantı Hatası", str(e))


class PersonnelMenuWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        l = QVBoxLayout(self)
        l.setContentsMargins(40, 30, 40, 40)
        top = QHBoxLayout()
        btn_back = QPushButton("ANA MENÜYE DÖN")
        btn_back.setObjectName("BackButton")
        btn_back.setFixedSize(180, 45)
        btn_back.clicked.connect(self.main_window.go_home)
        top.addWidget(btn_back)
        top.addStretch()
        l.addLayout(top)
        l.addStretch()
        c = QHBoxLayout()
        c.addStretch()
        box = QVBoxLayout()
        title = QLabel("VERİTABANI KONTROL MERKEZİ")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #00A8E8; margin-bottom: 30px; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignCenter)
        box.addWidget(title)
        b1 = QPushButton("PERSONEL YÖNETİMİ")
        b1.setFixedSize(500, 70)
        b1.setStyleSheet("font-size: 16px;")
        b1.clicked.connect(lambda: self.main_window.show_list_widget(self.main_window.list_workers))
        b2 = QPushButton("İSTASYON YÖNETİMİ")
        b2.setFixedSize(500, 70)
        b2.setStyleSheet("font-size: 16px;")
        b2.clicked.connect(lambda: self.main_window.show_list_widget(self.main_window.list_stations))
        box.addWidget(b1, alignment=Qt.AlignCenter)
        box.addSpacing(15)
        box.addWidget(b2, alignment=Qt.AlignCenter)
        c.addLayout(box)
        c.addStretch()
        l.addLayout(c)
        l.addStretch()


class AnalysisStatsWidget(QWidget):
    def __init__(self, is_general, main_window, back_target):
        super().__init__()
        self.main_window = main_window
        self.is_general = is_general
        self.back_target = back_target
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        top = QHBoxLayout()
        btn_back = QPushButton("GERİ DÖN")
        btn_back.setObjectName("BackButton")
        btn_back.setFixedSize(140, 40)
        btn_back.clicked.connect(lambda: self.main_window.stack.setCurrentWidget(self.back_target))
        title = "FABRİKA GENEL ANALİZ PANELİ" if is_general else "OPERATÖR PERFORMANS TAKİBİ"
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00A8E8; margin-left:20px;")
        top.addWidget(btn_back)
        top.addWidget(lbl_title)
        top.addStretch()
        main_layout.addLayout(top)

        if not is_general:
            selector = QHBoxLayout()
            lbl_select = QLabel("İşçi Seçiniz:")
            lbl_select.setStyleSheet("font-size:16px; font-weight:bold;")
            self.combo_w = QComboBox()
            self.combo_w.setFixedWidth(200)
            self.combo_w.setFixedHeight(35)
            self.combo_w.currentIndexChanged.connect(self.load_sessions)
            lbl_session = QLabel("Oturum:")
            lbl_session.setStyleSheet("font-size:16px; font-weight:bold; margin-left: 20px;")
            self.combo_s = QComboBox()
            self.combo_s.setFixedWidth(280)
            self.combo_s.setFixedHeight(35)
            self.combo_s.currentIndexChanged.connect(self.load_data)
            selector.addWidget(lbl_select)
            selector.addWidget(self.combo_w)
            selector.addWidget(lbl_session)
            selector.addWidget(self.combo_s)
            selector.addStretch()
            main_layout.addLayout(selector)

            self.session_info_lbl = QLabel("")
            self.session_info_lbl.setStyleSheet(
                "font-size: 15px; color: #E0E0E0; background-color: #1F1F1F; padding: 12px; border: 1px solid #333; border-radius: 3px; margin-top: 10px;")
            self.session_info_lbl.hide()
            main_layout.addWidget(self.session_info_lbl)

        self.chart_layout = QHBoxLayout()
        self.canvas_left = MplCanvas(self, width=6, height=4)
        self.canvas_right = MplCanvas(self, width=6, height=4)
        self.chart_layout.addWidget(self.canvas_left)
        self.chart_layout.addWidget(self.canvas_right)
        main_layout.addLayout(self.chart_layout, stretch=2)

        self.lbl_summary = QLabel()
        self.lbl_summary.setStyleSheet("font-size: 16px; color: #00A8E8; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(self.lbl_summary)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["KAYIT ID", "OTURUM ID", "İSTASYON", "BOYUN", "GÖVDE", "KOL", "BACAK", "GENEL SKOR", "RİSK SINIFI"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.table, stretch=1)

    def load_workers(self):
        try:
            self.combo_w.blockSignals(True)
            ws = REQ.get(f"{API_URL}/workers/", timeout=5).json()
            self.combo_w.clear()
            self.combo_w.addItems([w["full_name"] for w in ws])
            self.combo_w.blockSignals(False)
            self.load_sessions()
        except:
            pass

    def load_sessions(self):
        if self.is_general: return
        self.combo_s.blockSignals(True)
        self.combo_s.clear()
        worker_name = self.combo_w.currentText()
        if not worker_name:
            self.combo_s.blockSignals(False)
            return
        try:
            sessions = REQ.get(f"{API_URL}/worker_sessions/{worker_name}", timeout=5).json()
            for s in sessions:
                self.combo_s.addItem(f"Oturum #{s['id']} ({s['start_time']})", s)
        except:
            pass
        self.combo_s.blockSignals(False)
        self.load_data()

    def load_data(self):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        self.canvas_left.axes.clear()
        self.canvas_right.axes.clear()

        if not self.is_general and not self.combo_s.currentData():
            self.session_info_lbl.hide()
            self.lbl_summary.setText("BU İŞÇİYE AİT KAYITLI OTURUM BULUNAMADI.")
            self.canvas_left.draw()
            self.canvas_right.draw()
            self.table.setUpdatesEnabled(True)
            return

        try:
            if self.is_general:
                data_url = f"{API_URL}/reports/all/"
            else:
                session_data = self.combo_s.currentData()
                sid = session_data['id']
                data_url = f"{API_URL}/stats/session/{sid}"

                info_html = f"📍 <b>İSTASYON:</b> {session_data['location'].upper()} &nbsp;&nbsp;|&nbsp;&nbsp; 🕒 <b>TARİH:</b> {session_data['start_time']} <br> ⚙️ <b>PARAMETRELER:</b> Yük: {session_data['load']} Puan | Kavrama: {session_data['coupling']} Puan | Aktivite: {session_data['activity']} Puan | Bacak Durumu: {session_data['legs']} Puan"
                self.session_info_lbl.setText(info_html)
                self.session_info_lbl.show()

            table_data = REQ.get(data_url, timeout=5).json()

            if isinstance(table_data, list):
                self.lbl_summary.setText(f"GÖRÜNTÜLENEN VERİ NOKTASI: {len(table_data)} ADET")
                for row, item in enumerate(table_data[:50]):
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(str(item.get("id", ""))))
                    self.table.setItem(row, 1, QTableWidgetItem(str(item.get("session_id", ""))))
                    self.table.setItem(row, 2, QTableWidgetItem(str(item.get("location_name", "-")).upper()))
                    self.table.setItem(row, 3, QTableWidgetItem(str(item.get("neck_score", ""))))
                    self.table.setItem(row, 4, QTableWidgetItem(str(item.get("trunk_score", ""))))
                    self.table.setItem(row, 5, QTableWidgetItem(str(item.get("arm_score", ""))))
                    self.table.setItem(row, 6, QTableWidgetItem(str(item.get("leg_score", ""))))
                    self.table.setItem(row, 7, QTableWidgetItem(str(item.get("final_reba_score", ""))))
                    self.table.setItem(row, 8, QTableWidgetItem(str(item.get("risk_level", "")).upper()))

            if self.is_general:
                stats = REQ.get(f"{API_URL}/stats/stations/", timeout=5).json()
                if isinstance(stats, list) and len(stats) > 0:
                    names = [str(s.get("location_name", "Bilinmiyor")).upper() for s in stats]
                    reba_avgs = [float(s.get("avg_reba", 0)) for s in stats]
                    neck_avgs = [float(s.get("avg_neck", 0)) for s in stats]
                    trunk_avgs = [float(s.get("avg_trunk", 0)) for s in stats]

                    self.canvas_left.axes.bar(names, reba_avgs, color='#007ACC', alpha=0.9, edgecolor='#00A8E8')
                    self.canvas_left.axes.set_title("İSTASYON BAZLI ORTALAMA RİSK (REBA)", color='white', pad=15,
                                                    fontweight='bold')
                    self.canvas_left.axes.tick_params(axis='x', colors='white')
                    self.canvas_left.axes.tick_params(axis='y', colors='white')
                    self.canvas_left.axes.spines['bottom'].set_color('#333')
                    self.canvas_left.axes.spines['top'].set_color('none')
                    self.canvas_left.axes.spines['left'].set_color('#333')
                    self.canvas_left.axes.spines['right'].set_color('none')

                    x = np.arange(len(names))
                    width = 0.35
                    self.canvas_right.axes.bar(x - width / 2, neck_avgs, width, label='Boyun', color='#00C853')
                    self.canvas_right.axes.bar(x + width / 2, trunk_avgs, width, label='Gövde', color='#D32F2F')
                    self.canvas_right.axes.set_title("İSTASYONLARIN VÜCUT BÖLGESİ YÜKLERİ", color='white', pad=15,
                                                     fontweight='bold')
                    self.canvas_right.axes.set_xticks(x)
                    self.canvas_right.axes.set_xticklabels(names)
                    self.canvas_right.axes.tick_params(axis='x', colors='white')
                    self.canvas_right.axes.tick_params(axis='y', colors='white')
                    self.canvas_right.axes.spines['bottom'].set_color('#333')
                    self.canvas_right.axes.spines['top'].set_color('none')
                    self.canvas_left.axes.spines['left'].set_color('#333')
                    self.canvas_right.axes.spines['right'].set_color('none')
                    legend = self.canvas_right.axes.legend(facecolor='#1A1A1A', edgecolor='#333')
                    for text in legend.get_texts(): text.set_color("white")
            else:
                if isinstance(table_data, list) and len(table_data) > 0:
                    scores = [float(d.get('final_reba_score', 0)) for d in table_data]
                    times = [i for i in range(len(scores))]

                    self.canvas_left.axes.plot(times, scores, color='#00A8E8', marker='o', linewidth=2, markersize=6)
                    self.canvas_left.axes.fill_between(times, scores, color='#00A8E8', alpha=0.1)
                    self.canvas_left.axes.set_title("BU OTURUMDAKİ RİSK TRENDİ (Saniyelik)", color='white', pad=15,
                                                    fontweight='bold')
                    self.canvas_left.axes.tick_params(axis='x', colors='white')
                    self.canvas_left.axes.tick_params(axis='y', colors='white')
                    self.canvas_left.axes.spines['bottom'].set_color('#333')
                    self.canvas_left.axes.spines['top'].set_color('none')
                    self.canvas_left.axes.spines['left'].set_color('#333')
                    self.canvas_left.axes.spines['right'].set_color('none')

                    unique, counts = np.unique(scores, return_counts=True)
                    pie_colors = ['#00C853', '#FBC02D', '#FF9800', '#F44336', '#D32F2F', '#B71C1C']
                    colors = [pie_colors[i % len(pie_colors)] for i in range(len(unique))]
                    self.canvas_right.axes.pie(counts, labels=[f"Skor {int(u)}" for u in unique], autopct='%1.1f%%',
                                               startangle=90, colors=colors,
                                               textprops={'color': "white", 'fontweight': 'bold'})
                    self.canvas_right.axes.set_title("OTURUM RİSK DAĞILIMI", color='white', pad=15, fontweight='bold')

            self.canvas_left.figure.tight_layout()
            self.canvas_right.figure.tight_layout()
            self.canvas_left.draw()
            self.canvas_right.draw()
        except Exception as e:
            print("Grafik Çizim Hatası:", e)
        finally:
            self.table.setUpdatesEnabled(True)


class AnalysisMenuWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        l = QVBoxLayout(self)
        l.setContentsMargins(40, 30, 40, 40)
        top = QHBoxLayout()
        btn_back = QPushButton("ANA MENÜYE DÖN")
        btn_back.setObjectName("BackButton")
        btn_back.setFixedSize(180, 45)
        btn_back.clicked.connect(self.main_window.go_home)
        top.addWidget(btn_back)
        top.addStretch()
        l.addLayout(top)
        l.addStretch()
        c = QHBoxLayout()
        c.addStretch()
        box = QVBoxLayout()
        title = QLabel("ANALİZ VE RAPORLAMA MODÜLÜ")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #00A8E8; margin-bottom: 30px; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignCenter)
        box.addWidget(title)
        b1 = QPushButton("GENEL TESİS İSTATİSTİKLERİ VE GRAFİKLER")
        b1.setFixedSize(500, 70)
        b1.setStyleSheet("font-size: 16px;")
        b1.clicked.connect(lambda: self.main_window.show_stats_widget(self.main_window.stats_general))
        b2 = QPushButton("BİREYSEL OPERATÖR PERFORMANS GRAFİKLERİ")
        b2.setFixedSize(500, 70)
        b2.setStyleSheet("font-size: 16px;")
        b2.clicked.connect(lambda: self.main_window.show_stats_widget(self.main_window.stats_worker))
        box.addWidget(b1, alignment=Qt.AlignCenter)
        box.addSpacing(15)
        box.addWidget(b2, alignment=Qt.AlignCenter)
        c.addLayout(box)
        c.addStretch()
        l.addLayout(c)
        l.addStretch()


class MainMenuWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        l = QVBoxLayout(self)
        l.addStretch()
        c = QHBoxLayout()
        c.addStretch()
        box = QVBoxLayout()
        box.setAlignment(Qt.AlignCenter)
        t = QLabel("ERGONVISIO")
        t.setStyleSheet("font-size: 50px; font-weight: 900; color: #FFFFFF; margin-bottom: 5px; letter-spacing: 4px;")
        t.setAlignment(Qt.AlignCenter)
        st = QLabel("ENDÜSTRİYEL İSG ODAKLI REBA RİSK ANALİZ SİSTEMİ")
        st.setStyleSheet(
            "font-size: 16px; color: #00A8E8; margin-bottom: 60px; font-weight: bold; letter-spacing: 2px;")
        st.setAlignment(Qt.AlignCenter)
        box.addWidget(t)
        box.addWidget(st)
        b1 = QPushButton("ANALİZ")
        b1.setFixedSize(400, 70)
        b1.setStyleSheet("font-size: 18px; background-color: #007ACC; color: #FFFFFF; border: none;")
        b1.clicked.connect(self.main_window.go_setup)
        b2 = QPushButton("VERİTABANI YÖNETİMİ")
        b2.setFixedSize(400, 70)
        b2.setStyleSheet("font-size: 16px;")
        b2.clicked.connect(self.main_window.go_personnel)
        b3 = QPushButton("RAPORLAMA")
        b3.setFixedSize(400, 70)
        b3.setStyleSheet("font-size: 16px;")
        b3.clicked.connect(self.main_window.go_analysis_menu)
        for b in [b1, b2, b3]: box.addWidget(b, alignment=Qt.AlignCenter); box.addSpacing(15)
        c.addLayout(box)
        c.addStretch()
        l.addLayout(c)
        l.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ErgonVisio - İSG Kontrol Paneli")
        self.setMinimumSize(1000, 700)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.main_menu = MainMenuWidget(self)
        self.setup_widget = SetupAnalysisWidget(self)
        self.personnel_menu = PersonnelMenuWidget(self)
        self.analysis_menu = AnalysisMenuWidget(self)
        self.list_workers = ListWidget("PERSONEL KAYITLARI", ["SİSTEM ID", "AD SOYAD", "DEPARTMAN"],
                                       ["id", "full_name", "department"], "workers", AddWorkerDialog, self,
                                       self.personnel_menu)
        self.list_stations = ListWidget("İSTASYON KAYITLARI", ["LOKASYON ID", "LOKASYON ADI", "KAMERA BAĞLANTISI"],
                                        ["id", "location_name", "camera_id"], "workstations", AddLocationDialog, self,
                                        self.personnel_menu)
        self.stats_general = AnalysisStatsWidget(True, self, self.analysis_menu)
        self.stats_worker = AnalysisStatsWidget(False, self, self.analysis_menu)

        for w in [self.main_menu, self.setup_widget, self.personnel_menu, self.analysis_menu, self.list_workers,
                  self.list_stations, self.stats_general, self.stats_worker]:
            self.stack.addWidget(w)

        self.analysis_widget = None

    def go_home(self):
        if self.analysis_widget and hasattr(self.analysis_widget, 'thread'): self.analysis_widget.thread.stop()
        self.stack.setCurrentWidget(self.main_menu)

    def go_setup(self):
        self.setup_widget.load_api()
        self.setup_widget.te_time.setTime(QTime.currentTime())
        self.stack.setCurrentWidget(self.setup_widget)

    def go_personnel(self):
        self.stack.setCurrentWidget(self.personnel_menu)

    def go_analysis_menu(self):
        self.stack.setCurrentWidget(self.analysis_menu)

    def start_live_analysis(self, data):
        self.analysis_widget = AnalysisWidget(self, data["w"], data["l"], data["t"], data["p"], data["id"],
                                              data["params"])
        self.stack.addWidget(self.analysis_widget)
        self.stack.setCurrentWidget(self.analysis_widget)

    def show_list_widget(self, target_widget):
        target_widget.load_data()
        self.stack.setCurrentWidget(target_widget)

    def show_stats_widget(self, target_widget):
        if not target_widget.is_general:
            target_widget.load_workers()
        target_widget.load_data()
        self.stack.setCurrentWidget(target_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(INDUSTRIAL_STYLE)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())