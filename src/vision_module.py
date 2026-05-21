import cv2
import mediapipe as mp
import time
import requests
from reba_analyzer import RebaAnalyzer

# FastApi sunucu adresi
API_URL = "http://127.0.0.1:8001"

# PoseDetector sınıfı
class PoseDetector:
    def __init__(self, static_image_mode=False, model_complexity=1, smooth_landmarks=True,
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            smooth_landmarks=smooth_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.results = None

    def find_pose(self, image, draw=True):
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)
        if self.results.pose_landmarks and draw:
            self.mp_drawing.draw_landmarks(
                image, self.results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
        return image

    def get_landmarks(self):
        landmark_list = []
        if self.results and self.results.pose_landmarks:
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                landmark_list.append([id, lm.x, lm.y, lm.z])
        return landmark_list


def main(source=0):
    # 1. API'ye Bağlan ve Session başlat
    try:
        print("API'ye bağlanılıyor...")
        response = requests.get(f"{API_URL}/init_demo/")

        # SADECE 200 BAŞARILI KODU GELİRSE DEVAM ET
        if response.status_code == 200:
            session_id = response.json().get("session_id")
            if session_id is None:
                print("HATA: Sunucu 200 döndürdü ama session_id boş!")
                return
            print(f"BAŞARILI! Analiz Oturum ID: {session_id} ile başlatıldı.")
        else:
            print(f"KRİTİK HATA: API sunucusu {response.status_code} hatası döndürdü!")
            print("Sunucu Cevabı:", response.text)
            return

    except Exception as e:
        print("HATA: API'ye ulaşılamadı. FastAPI sunucusunun (Uvicorn) çalıştığından emin olun!")
        return

    cap = cv2.VideoCapture(source)
    detector = PoseDetector()
    analyzer = RebaAnalyzer()

    # Zamanlayıcıyı Başlat (Saniyede 1 kez veri göndermek için)
    last_log_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame = detector.find_pose(frame)
        landmarks = detector.get_landmarks()

        if len(landmarks) != 0:
            ear = landmarks[7][1:3]
            shoulder = landmarks[11][1:3]
            elbow = landmarks[13][1:3]
            wrist = landmarks[15][1:3]
            hip = landmarks[23][1:3]
            index_finger = landmarks[19][1:3]

            points = (ear, shoulder, elbow, wrist, hip, index_finger)

            # Analizi Yap
            reba_score, risk_text, risk_color = analyzer.calculate_final_reba(points)

            # API için alt skorları al
            neck_sc = analyzer.get_neck_score(ear, shoulder)
            trunk_sc = analyzer.get_trunk_score(shoulder, hip)
            arm_sc = analyzer.get_upper_arm_score(shoulder, elbow)

            # Veritabanı loglama işlemmi(FPS düşmesini engeller...
            current_time = time.time()
            if current_time - last_log_time >= 1.0:  # Eğer 1 saniye geçtiyse
                is_crit = 1 if reba_score >= 8 else 0  # 8 ve üzeri yüksek riskli sayılır

                payload = {
                    "session_id": session_id,
                    "neck": neck_sc,
                    "trunk": trunk_sc,
                    "arm": arm_sc,
                    "final_score": reba_score,
                    "risk_level": risk_text,
                    "is_critical": is_crit
                }

                # Arkaplanda API'ye postala (Hata ayıklama sürümü)
                try:
                    res = requests.post(f"{API_URL}/log_risk/", params=payload)
                    if res.status_code == 200:
                        print(f"BAŞARILI: Skor {reba_score} veritabanına yazıldı!")
                    else:
                        print(f"API REDDETTİ (Hata {res.status_code}):", res.text)
                except requests.exceptions.RequestException as e:
                    print("AĞ HATASI (API'ye ulaşılamıyor):", e)

                last_log_time = current_time  # Zamanlayıcıyı sıfırla

if __name__ == "__main__":
    pass