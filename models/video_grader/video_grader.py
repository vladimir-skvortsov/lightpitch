import json

import cv2
import mediapipe as mp
import numpy as np


class VideoGrader:
    def __init__(self):
        # --- MediaPipe solutions
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.mp_face = mp.solutions.face_mesh
        self.face = self.mp_face.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )

        # --- Heuristic thresholds (tunable)
        self.EAR_CLOSED_THR = 0.18  # Eye Aspect Ratio threshold below -> closed
        self.WRIST_VIS_THR = 0.5  # Visibility confidence for wrists
        self.SHOULDERS_Z_DIFF_THR = 0.20  # |z_L - z_R| below -> facing camera
        self.SHOULDERS_MIN_WIDTH = 0.10  # |x_L - x_R| above -> not fully profile

    # =======================
    # Face helpers
    # =======================
    def _eye_aspect_ratio(self, landmarks, eye_indices) -> float:
        """Eye Aspect Ratio (EAR) for eye openness.
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        """
        p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_indices]
        vertical1 = np.linalg.norm(np.array([p2.x, p2.y]) - np.array([p6.x, p6.y]))
        vertical2 = np.linalg.norm(np.array([p3.x, p3.y]) - np.array([p5.x, p5.y]))
        horizontal = np.linalg.norm(np.array([p1.x, p1.y]) - np.array([p4.x, p4.y]))
        return (vertical1 + vertical2) / (2.0 * horizontal + 1e-6)

    def _analyze_eyes(self, frame) -> dict:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face.process(frame_rgb)

        if not results.multi_face_landmarks:
            return {
                'left_eye': 'not_visible',
                'right_eye': 'not_visible',
                'both_eyes_visible_open': False,
            }

        face_landmarks = results.multi_face_landmarks[0].landmark

        LEFT_EYE = [33, 160, 158, 133, 153, 144]
        RIGHT_EYE = [362, 385, 387, 263, 373, 380]

        left_ear = self._eye_aspect_ratio(face_landmarks, LEFT_EYE)
        right_ear = self._eye_aspect_ratio(face_landmarks, RIGHT_EYE)

        def eye_status(ear: float) -> str:
            if ear < 0.12:
                return 'closed'
            else:
                return 'open'

        left_state = eye_status(left_ear)
        right_state = eye_status(right_ear)

        both_eyes_visible_open = left_state == 'open' and right_state == 'open'

        return {
            'left_eye': left_state,
            'right_eye': right_state,
            'both_eyes_visible_open': both_eyes_visible_open,
        }

    def _detect_smile_like(self, frame) -> bool:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face.process(frame_rgb)
        if not results.multi_face_landmarks:
            return False

        lm = results.multi_face_landmarks[0].landmark

        left_corner = lm[61]
        right_corner = lm[291]
        upper_lip = lm[13]
        lower_lip = lm[14]

        left_eye_outer = lm[33]
        right_eye_outer = lm[263]
        top_face = lm[10]
        chin = lm[152]

        mouth_center_y = 0.5 * (upper_lip.y + lower_lip.y)
        corners_avg_y = 0.5 * (left_corner.y + right_corner.y)

        corner_raise = mouth_center_y - corners_avg_y

        face_h = np.linalg.norm(np.array([top_face.x, top_face.y]) - np.array([chin.x, chin.y]))
        eye_dist = np.linalg.norm(
            np.array([left_eye_outer.x, left_eye_outer.y]) - np.array([right_eye_outer.x, right_eye_outer.y])
        )
        mouth_width = np.linalg.norm(
            np.array([left_corner.x, left_corner.y]) - np.array([right_corner.x, right_corner.y])
        )

        corner_raise_norm = corner_raise / (face_h + 1e-6)
        width_ratio = mouth_width / (eye_dist + 1e-6)

        return (corner_raise_norm > 0.003) and (width_ratio > 0.75)

    @staticmethod
    def _in_frame_xy(lm):
        return (0.0 <= lm.x <= 1.0) and (0.0 <= lm.y <= 1.0)

    def _analyze_pose(self, frame) -> dict:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        out = {
            'pose_detected': False,
            'hands_present': False,
            'pose': False,
        }

        if not results.pose_landmarks:
            return out

        lms = results.pose_landmarks.landmark
        out['pose_detected'] = True

        lw = lms[self.mp_pose.PoseLandmark.LEFT_WRIST]
        rw = lms[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        hands_present = (lw.visibility > self.WRIST_VIS_THR and self._in_frame_xy(lw)) or (
            rw.visibility > self.WRIST_VIS_THR and self._in_frame_xy(rw)
        )
        out['hands_present'] = bool(hands_present)

        ls = lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        rs = lms[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        shoulders_ok = all(
            [
                self._in_frame_xy(ls),
                self._in_frame_xy(rs),
                ls.visibility > 0.5,
                rs.visibility > 0.5,
            ]
        )
        if shoulders_ok:
            z_diff = abs(ls.z - rs.z)
            width = abs(ls.x - rs.x)
            out['pose'] = (z_diff < self.SHOULDERS_Z_DIFF_THR) and (width > self.SHOULDERS_MIN_WIDTH)

        out['landmarks'] = [{'id': i, 'x': lm.x, 'y': lm.y, 'z': lm.z, 'v': lm.visibility} for i, lm in enumerate(lms)]
        return out

    def split_video(self, video_path: str, step_seconds: int = 1) -> list:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = max(1, int(fps * step_seconds))

        frames = []
        frame_id = 0
        success, frame = cap.read()
        while success:
            if frame_id % frame_interval == 0:
                frames.append(frame.copy())
            success, frame = cap.read()
            frame_id += 1

        cap.release()
        return frames

    def process_frame(self, frame) -> dict:
        pose_data = self._analyze_pose(frame)
        eye_data = self._analyze_eyes(frame)
        smile_like = self._detect_smile_like(frame)

        pose_data['open_pose'] = pose_data.get('pose', False)

        pose_data.update(eye_data)
        pose_data['smile_like'] = bool(smile_like)

        return pose_data

    def analyze_frames(self, frames: list) -> list:
        results = []
        for i, frame in enumerate(frames):
            frame_result = self.process_frame(frame)
            frame_result['frame_id'] = i
            results.append(frame_result)
        return results

    def to_json(self, analysis_results: list) -> str:
        return json.dumps(analysis_results, indent=2)

    def final_score(self, analysis_results: list) -> dict:
        total_frames = len(analysis_results)

        if total_frames == 0:
            return {
                'name': 'Невербальная коммуникация',
                'value': 0.0,
                'metrics': [
                    {'label': 'Взгляд', 'status': 'error', 'value': 0.0},
                    {'label': 'Жестикуляция', 'status': 'error', 'value': 0.0},
                    {'label': 'Открытая поза', 'status': 'error', 'value': 0.0},
                ],
                'diagnostics': [
                    {
                        'label': 'Впечатление',
                        'sublabel': 'улыбка',
                        'status': 'warning',
                        'comment': 'Добродушное отношение к публике вызовет благосклонность (улыбнитесь хотя бы раз)',
                    }
                ],
            }

        eyes_frames = sum(1 for r in analysis_results if r.get('both_eyes_visible_open'))
        smile_present = any(bool(r.get('smile_like')) for r in analysis_results)
        gest_frames = sum(1 for r in analysis_results if r.get('hands_present'))
        pose_frames = sum(1 for r in analysis_results if r.get('pose') or r.get('open_pose'))

        eyes_score = eyes_frames / total_frames
        gesticulation_ratio = gest_frames / total_frames
        pose_ratio = pose_frames / total_frames

        composite = float(np.mean([eyes_score, gesticulation_ratio, pose_ratio]) - 0.05 * int(not smile_present))

        def status(value: float, good_thr: float, warn_thr: float) -> str:
            if value >= good_thr:
                return 'good'
            if value >= warn_thr:
                return 'warning'
            return 'error'

        metrics = [
            {
                'label': 'Взгляд',
                'status': status(eyes_score, 0.90, 0.70),
                'value': round(eyes_score, 2),
            },
            {
                'label': 'Жестикуляция',
                'status': status(gesticulation_ratio, 0.25, 0.10),
                'value': round(gesticulation_ratio, 2),
            },
            {
                'label': 'Открытая поза',
                'status': status(pose_ratio, 0.70, 0.40),
                'value': round(pose_ratio, 2),
            },
        ]

        diagnostics = [
            {
                'label': 'Впечатление',
                'sublabel': 'улыбка',
                'status': 'good' if smile_present else 'warning',
                'comment': 'Добродушное отношение к публике вызовет благосклонность (улыбнитесь хотя бы раз)',
            },
            {
                'label': 'Зрительный контакт',
                'status': status(eyes_score, 0.95, 0.20),
                'comment': 'Старайтесь держать зрительный контакт с публикой всё выступление',
            },
        ]

        return {
            'name': 'Невербальная коммуникация',
            'value': round(composite, 2),
            'metrics': metrics,
            'diagnostics': diagnostics,
        }


if __name__ == '__main__':
    grader = VideoGrader()

    frames = grader.split_video('frames/IMG_4612.MOV')

    results = grader.analyze_frames(frames)

    report = grader.final_score(results)
    print(json.dumps(report, ensure_ascii=False, indent=2))
