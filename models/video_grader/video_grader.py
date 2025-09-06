import json

import cv2
import mediapipe as mp
import numpy as np


class VideoGrader:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

        self.mp_face = mp.solutions.face_mesh
        self.face = self.mp_face.FaceMesh(
            static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5
        )

    def _eye_aspect_ratio(self, landmarks, eye_indices) -> float:
        """
        Eye Aspect Ratio (EAR) для определения открытости глаза.
        landmarks: список из 468 точек лица
        eye_indices: индексы точек для глаза

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
            return {'left_eye': 'not_visible', 'right_eye': 'not_visible'}

        face_landmarks = results.multi_face_landmarks[0].landmark

        LEFT_EYE = [33, 160, 158, 133, 153, 144]
        RIGHT_EYE = [362, 385, 387, 263, 373, 380]

        left_ear = self._eye_aspect_ratio(face_landmarks, LEFT_EYE)
        right_ear = self._eye_aspect_ratio(face_landmarks, RIGHT_EYE)

        def eye_status(ear: float) -> str:
            if ear < 0.18:
                return 'closed'
            else:
                return 'open'

        return {
            'left_eye': eye_status(left_ear),
            'right_eye': eye_status(right_ear),
        }

    def split_video(self, video_path: str, step_seconds: int = 1) -> list:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * step_seconds)

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
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        pose_data = {'pose_detected': False}

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE]

            wrists_distance = abs(left_wrist.x - right_wrist.x)
            open_pose = wrists_distance > 0.2

            eye_contact = 0.4 < nose.x < 0.6

            pose_data = {
                'pose_detected': True,
                'open_pose': open_pose,
                'eye_contact': eye_contact,
                'landmarks': [{'id': i, 'x': lm.x, 'y': lm.y, 'z': lm.z} for i, lm in enumerate(landmarks)],
            }

        eye_data = self._analyze_eyes(frame)
        pose_data.update(eye_data)

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
        open_frames = sum(1 for r in analysis_results if r.get('open_pose'))
        eye_frames = sum(1 for r in analysis_results if r.get('eye_contact'))
        open_eye_frames = sum(
            1 for r in analysis_results if r.get('left_eye') == 'open' and r.get('right_eye') == 'open'
        )

        return {
            'open_pose_ratio': open_frames / total_frames if total_frames else 0,
            'eye_contact_ratio': eye_frames / total_frames if total_frames else 0,
            'open_eyes_ratio': open_eye_frames / total_frames if total_frames else 0,
            'final_score': round((open_frames + eye_frames + open_eye_frames) / (3 * total_frames) * 100, 2)
            if total_frames
            else 0,
        }


if __name__ == '__main__':
    grader = VideoGrader()

    frame_paths = ['frames/frame4.jpg']
    frames = [cv2.imread(p) for p in frame_paths]

    results = grader.analyze_frames(frames)

    print('JSON results:')
    print(grader.to_json(results))

    print('\nFinal score:', grader.final_score(results))
