import cv2
import mediapipe as mp

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
                image,
                self.results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )
        return image

    def get_landmarks(self):

        landmark_list = []
        if self.results and self.results.pose_landmarks:
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                # lm.x, lm.y, lm.z değerleri 0 ile 1 arasında normalize edilmiş değerlerdir
                landmark_list.append([id, lm.x, lm.y, lm.z])
        return landmark_list

def main():

    cap = cv2.VideoCapture(0)
    detector = PoseDetector()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = detector.find_pose(frame)



        cv2.imshow('Ergonomic Risk Assessment - OOP Test', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()