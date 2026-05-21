import math


class RebaAnalyzer:
    def __init__(self):
        """Tam standart REBA Değerlendirme Matris Tablolu"""
        self.load_score = 0
        self.coupling_score = 0
        self.activity_score = 1
        self.legs_score_base = 1

        # REBA MATRİS TABLOLARI

        # TABLE A: Gövde (1-5), Boyun (1-3), Bacak (1-4)
        self.TABLE_A = [
            # Trunk 1
            [[1, 2, 3, 4], [1, 2, 3, 4], [3, 3, 5, 6]],
            # Trunk 2
            [[2, 3, 4, 5], [3, 4, 5, 6], [4, 5, 6, 7]],
            # Trunk 3
            [[2, 4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]],
            # Trunk 4
            [[3, 5, 6, 7], [5, 6, 7, 8], [6, 7, 8, 9]],
            # Trunk 5
            [[4, 6, 7, 8], [6, 7, 8, 9], [7, 8, 9, 9]]
        ]

        # TABLE B: Üst Kol (1-6), Alt Kol (1-2), Bilek (1-3)
        self.TABLE_B = [
            # Upper Arm 1
            [[1, 2, 2], [1, 2, 3]],
            # Upper Arm 2
            [[1, 2, 3], [2, 3, 4]],
            # Upper Arm 3
            [[3, 4, 5], [4, 5, 5]],
            # Upper Arm 4
            [[4, 5, 5], [5, 6, 7]],
            # Upper Arm 5
            [[6, 7, 8], [7, 8, 8]],
            # Upper Arm 6
            [[7, 8, 8], [8, 9, 9]]
        ]

        # TABLE C: Score A (1-12) x Score B (1-12)
        self.TABLE_C = [
            [1, 1, 1, 2, 3, 3, 4, 5, 6, 7, 7, 7],  # Score A = 1
            [1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8],  # Score A = 2
            [2, 3, 3, 3, 4, 5, 6, 7, 7, 8, 8, 8],  # Score A = 3
            [3, 4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9],  # Score A = 4
            [4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9, 9],  # Score A = 5
            [6, 6, 6, 7, 8, 8, 9, 9, 10, 10, 10, 10],  # Score A = 6
            [7, 7, 7, 8, 9, 9, 9, 10, 10, 11, 11, 11],  # Score A = 7
            [8, 8, 8, 9, 10, 10, 10, 10, 10, 11, 11, 11],  # Score A = 8
            [9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12],  # Score A = 9
            [10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 12],  # Score A = 10
            [11, 11, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12],  # Score A = 11
            [12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12]  # Score A = 12
        ]

    def set_parameters(self, load, coupling, activity, legs):
        self.load_score = load
        self.coupling_score = coupling
        self.activity_score = activity
        self.legs_score_base = legs

    def calculate_angle_3points(self, p1, p2, p3):
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        angle_rad = math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2)
        angle_deg = abs(math.degrees(angle_rad))
        if angle_deg > 180:
            angle_deg = 360 - angle_deg
        return int(angle_deg)

    def calculate_angle_vertical(self, top_point, bottom_point):
        x1, y1 = top_point
        x2, y2 = bottom_point
        delta_x = x1 - x2
        delta_y = y1 - y2
        angle_rad = math.atan2(abs(delta_x), abs(delta_y))
        return int(math.degrees(angle_rad))

    def get_neck_score(self, ear, shoulder):
        angle = self.calculate_angle_vertical(ear, shoulder)
        return 1 if 0 <= angle <= 20 else 2

    def get_trunk_score(self, shoulder, hip):
        angle = self.calculate_angle_vertical(shoulder, hip)
        if angle == 0:
            return 1
        elif 0 < angle <= 20:
            return 2
        elif 20 < angle <= 60:
            return 3
        else:
            return 4

    def get_legs_score(self):
        return self.legs_score_base

    def get_upper_arm_score(self, shoulder, elbow):
        angle = self.calculate_angle_vertical(shoulder, elbow)
        if 0 <= angle <= 20:
            return 1
        elif 20 < angle <= 45:
            return 2
        elif 45 < angle <= 90:
            return 3
        else:
            return 4

    def get_lower_arm_score(self, shoulder, elbow, wrist):
        angle = self.calculate_angle_3points(shoulder, elbow, wrist)
        return 1 if 60 <= angle <= 100 else 2

    def get_wrist_score(self, elbow, wrist, index_finger):
        angle = self.calculate_angle_3points(elbow, wrist, index_finger)
        return 1 if 165 <= angle <= 195 else 2

    # MATRİS TABLO HESAPLAMALAR
    def get_table_a_score(self, trunk, neck, legs):
        # Listeler 0'dan başladığı için skorlardan 1 çıkararak indeksi buluyoruz
        t_idx = max(0, min(trunk - 1, 4))
        n_idx = max(0, min(neck - 1, 2))
        l_idx = max(0, min(legs - 1, 3))
        return self.TABLE_A[t_idx][n_idx][l_idx]

    def get_table_b_score(self, upper_arm, lower_arm, wrist):
        ua_idx = max(0, min(upper_arm - 1, 5))
        la_idx = max(0, min(lower_arm - 1, 1))
        w_idx = max(0, min(wrist - 1, 2))
        return self.TABLE_B[ua_idx][la_idx][w_idx]

    def get_table_c_score(self, score_a, score_b):
        a_idx = max(0, min(score_a - 1, 11))
        b_idx = max(0, min(score_b - 1, 11))
        return self.TABLE_C[a_idx][b_idx]

    def calculate_final_reba(self, points):
        ear, shoulder, elbow, wrist, hip, index_finger = points

        neck = self.get_neck_score(ear, shoulder)
        trunk = self.get_trunk_score(shoulder, hip)
        legs = self.get_legs_score()

        upper_arm = self.get_upper_arm_score(shoulder, elbow)
        lower_arm = self.get_lower_arm_score(shoulder, elbow, wrist)
        wrist_sc = self.get_wrist_score(elbow, wrist, index_finger)

        # Matrislerden gelen ana skorlar + Girlen uzman parametreleri
        score_a = self.get_table_a_score(trunk, neck, legs) + self.load_score
        score_b = self.get_table_b_score(upper_arm, lower_arm, wrist_sc) + self.coupling_score

        # C Matrisi Skoru
        score_c = self.get_table_c_score(score_a, score_b)

        # Nihai Skor
        final_reba = score_c + self.activity_score

        # Risk Seviyesi
        if final_reba <= 1:
            return final_reba, "Ihmal Edilebilir", (0, 255, 0)
        elif 2 <= final_reba <= 3:
            return final_reba, "Dusuk Risk", (0, 200, 0)
        elif 4 <= final_reba <= 7:
            return final_reba, "Orta Risk (Mudahale Gerekebilir)", (0, 165, 255)
        elif 8 <= final_reba <= 10:
            return final_reba, "Yuksek Risk (Yakin Zamanda Mudahale)", (0, 0, 255)
        else:
            return final_reba, "Cok Yuksek Risk (HEMEN MUDAHALE!)", (0, 0, 139)