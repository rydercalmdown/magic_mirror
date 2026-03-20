"""
ActionClipService: capture rolling 5s clips to disk, extract landmarks with MediaPipe,
classify with the existing model pipeline, and write result JSON.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Tuple, Dict

import cv2
import numpy as np


@dataclass
class ClipResult:
    clip_path: str
    start_ts: float
    end_ts: float
    fps: float
    frames: int
    mediapipe_ms: float
    classify_ms: float
    label: Optional[str]
    landmarks_path: Optional[str]
    label_confidence: Optional[float] = None
    class_confidences: Optional[Dict[str, float]] = None


class ActionClipService:
    def __init__(
        self,
        clips_dir: Path,
        results_dir: Path,
        training_dir: Path,
        camera_index: int = 0,
        clip_seconds: float = 5.0,
        target_fps: float = 30.0,
    ):
        self.clips_dir = clips_dir
        self.results_dir = results_dir
        self.training_dir = training_dir
        self.enabled = True
        self.capture_thread: Optional[threading.Thread] = None
        self.process_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.camera_index = camera_index
        self.clip_seconds = clip_seconds
        self.target_fps = target_fps

        # queue of finished clips awaiting processing
        self._process_queue: List[Tuple[str, float, float, float, int]] = []  # (path, start_ts, end_ts, fps, frames)
        self._queue_lock = threading.Lock()

        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Load the training pipeline lazily when first used
        self.pipeline = None
        # Carry measured FPS from previous segment to set container FPS for next writer
        self._next_segment_fps: float = target_fps

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        self.process_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.process_thread.start()

    def stop(self):
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join()
        if self.process_thread:
            self.process_thread.join()

    def _open_writer(self, base_path: Path, fps: float, size: Tuple[int, int]) -> Tuple[cv2.VideoWriter, str]:
        """Open a writer using MJPG/AVI for best macOS compatibility. Returns (writer, actual_path)."""
        width, height = size
        avi_path = str(base_path.with_suffix('.avi'))
        writer = cv2.VideoWriter(avi_path, cv2.VideoWriter_fourcc(*'MJPG'), fps, (width, height))
        return writer, avi_path

    def _capture_loop(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"❌ ActionClipService: Could not open camera {self.camera_index}")
            self.is_running = False
            return
        # Try to request typical settings
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Segment rolling
        segment_start_mono = time.monotonic()
        ts_id = int(time.time())
        base = self.clips_dir / f"clip_{ts_id}"
        # determine actual frame size after first frame
        ok, frame = cap.read()
        if not ok:
            print("⚠️ ActionClipService: Initial frame read failed")
            cap.release()
            self.is_running = False
            return
        h, w = frame.shape[:2]
        # Try to use camera-reported FPS for better timing if available
        cam_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        if not cam_fps or cam_fps <= 1.0 or cam_fps > 120.0:
            cam_fps = self._next_segment_fps
        writer, clip_path = self._open_writer(base, cam_fps, (w, h))
        if not writer or not writer.isOpened():
            print("❌ ActionClipService: VideoWriter failed to open")
            cap.release()
            self.is_running = False
            return
        frames_written = 0
        start_ts = segment_start_mono
        last_frame_time = time.monotonic()
        while self.is_running:
            ok, frame = cap.read()
            now_mono = time.monotonic()
            if not ok:
                # brief pause and retry
                time.sleep(0.005)
                continue
            writer.write(frame)
            frames_written += 1

            # Rotate segment every clip_seconds
            if (now_mono - segment_start_mono) >= self.clip_seconds:
                writer.release()
                end_ts = now_mono
                # Measure actual FPS during this segment and store for the next container
                seg_duration = max(0.001, end_ts - start_ts)
                actual_fps = max(1.0, min(120.0, frames_written / seg_duration))
                self._next_segment_fps = round(actual_fps, 1)
                with self._queue_lock:
                    self._process_queue.append((clip_path, start_ts, end_ts, self.target_fps, frames_written))
                # start a new segment
                segment_start_mono = now_mono
                start_ts = now_mono
                ts_id = int(time.time())
                base = self.clips_dir / f"clip_{ts_id}"
                writer, clip_path = self._open_writer(base, self._next_segment_fps, (w, h))
                frames_written = 0

            # Optional: tiny sleep to avoid 100% CPU if camera faster
            dt = now_mono - last_frame_time
            if dt < (1.0 / max(1.0, self.target_fps)):
                time.sleep((1.0 / self.target_fps) - dt)
            last_frame_time = time.monotonic()

        # Cleanup
        try:
            writer.release()
        except Exception:
            pass
        cap.release()

    def _processing_loop(self):
        while self.is_running:
            item = None
            with self._queue_lock:
                if self._process_queue:
                    item = self._process_queue.pop(0)
            if not item:
                time.sleep(0.05)
                continue
            clip_path, start_ts, end_ts, fps, frames = item

            # Process with mediapipe-Holistic and model from training pipeline
            mediapipe_ms = 0.0
            classify_ms = 0.0
            label: Optional[str] = None
            landmarks_path: Optional[str] = None
            label_confidence: Optional[float] = None
            class_confidences: Optional[Dict[str, float]] = None
            try:
                import mediapipe as mp  # lazy import to avoid startup cost
                basename = Path(clip_path).stem
                landmarks_path = str(self.results_dir / f"{basename}_landmarks.json")

                # Prepare classifier pipeline lazily, ensure relative model files resolve
                if self.pipeline is None:
                    try:
                        import sys, os
                        sys.path.append(str(self.training_dir))
                        from realtime_inference import ActionRecognizer as TrainingActionRecognizer  # type: ignore
                        prev = os.getcwd()
                        try:
                            os.chdir(self.training_dir)
                            self.pipeline = TrainingActionRecognizer(model_path=str(self.training_dir / 'models' / 'action_recognition_model.pth'))
                        finally:
                            os.chdir(prev)
                    except Exception:
                        self.pipeline = None

                cap2 = cv2.VideoCapture(clip_path)
                holistic = mp.solutions.holistic.Holistic(
                    static_image_mode=False,
                    model_complexity=1,
                    enable_segmentation=False,
                    refine_face_landmarks=False
                )
                frames_landmarks: List[List[float]] = []
                label_counts: dict = {}
                try:
                    while True:
                        ok2, f2 = cap2.read()
                        if not ok2:
                            break
                        # Landmark extraction timing
                        lm_t0 = time.perf_counter()
                        rgb = cv2.cvtColor(f2, cv2.COLOR_BGR2RGB)
                        results = holistic.process(rgb)
                        lm_vec = []
                        # Use training pipeline's feature layout for consistency
                        if self.pipeline is not None:
                            try:
                                vec = self.pipeline.extract_landmarks(results)
                                lm_vec = vec.astype(float).tolist()
                            except Exception:
                                lm_vec = []
                        else:
                            lm_vec = []
                        lm_t1 = time.perf_counter()
                        mediapipe_ms += (lm_t1 - lm_t0) * 1000.0
                        frames_landmarks.append(lm_vec)

                        # Push into pipeline buffer and get predictions periodically
                        if self.pipeline is not None:
                            try:
                                # Append landmarks into buffer directly to mirror training
                                if lm_vec:
                                    self.pipeline.landmark_buffer.append(np.array(lm_vec))
                                if len(self.pipeline.landmark_buffer) >= getattr(self.pipeline, 'sequence_length', 0):
                                    cls_t0 = time.perf_counter()
                                    act, conf = self.pipeline.predict_action()
                                    cls_t1 = time.perf_counter()
                                    classify_ms += (cls_t1 - cls_t0) * 1000.0
                                    if act and act not in ('no_action', 'collecting_data'):
                                        label_counts[act] = label_counts.get(act, 0) + 1
                            except Exception:
                                pass
                finally:
                    cap2.release()
                    holistic.close()

                # Decide clip label: prefer direct sequence classification over votes
                if self.pipeline is not None and frames_landmarks:
                    try:
                        seq_len = getattr(self.pipeline, 'sequence_length', 120)
                        expected_features = int(getattr(self.pipeline.scaler, 'n_features_in_', len(frames_landmarks[0]) if frames_landmarks else 0))
                        sequence = np.asarray(frames_landmarks, dtype=float)
                        # Ensure feature dimension matches scaler
                        cur_feat = sequence.shape[1] if sequence.ndim == 2 else 0
                        if cur_feat and cur_feat < expected_features:
                            pad_cols = expected_features - cur_feat
                            sequence = np.concatenate([sequence, np.zeros((sequence.shape[0], pad_cols))], axis=1)
                        elif cur_feat and cur_feat > expected_features:
                            sequence = sequence[:, :expected_features]
                        # Pad/truncate time dimension to sequence length
                        if sequence.shape[0] < seq_len:
                            pad_rows = seq_len - sequence.shape[0]
                            sequence = np.concatenate([sequence, np.zeros((pad_rows, sequence.shape[1]))], axis=0)
                        elif sequence.shape[0] > seq_len:
                            sequence = sequence[-seq_len:, :]
                        # Scale and infer
                        sequence_scaled = self.pipeline.scaler.transform(sequence.reshape(-1, sequence.shape[-1]))
                        sequence_scaled = sequence_scaled.reshape(1, seq_len, -1)
                        import torch  # lazy import
                        with torch.no_grad():
                            logits = self.pipeline.model(torch.FloatTensor(sequence_scaled))
                            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
                            idx = int(np.argmax(probs))
                            label = self.pipeline.label_encoder.inverse_transform([idx])[0]
                            label_confidence = float(probs[idx])
                            # Map confidences to class names
                            if hasattr(self.pipeline, 'classes'):
                                class_confidences = {str(cls): float(probs[i]) for i, cls in enumerate(self.pipeline.classes)}
                    except Exception:
                        # fallback to majority vote
                        label = None
                if (label is None) and label_counts:
                    label = max(label_counts.items(), key=lambda kv: kv[1])[0]

                # Write landmarks JSON (frames -> flattened training feature vectors)
                with open(landmarks_path, 'w') as lf:
                    json.dump({'frames': frames_landmarks}, lf)
            except Exception:
                # On failure, leave label None and no landmarks
                pass

            # Write result JSON
            result = ClipResult(
                clip_path=clip_path,
                start_ts=start_ts,
                end_ts=end_ts,
                fps=fps,
                frames=frames,
                mediapipe_ms=round(mediapipe_ms, 2),
                classify_ms=round(classify_ms, 2),
                label=label,
                landmarks_path=landmarks_path,
                label_confidence=label_confidence,
                class_confidences=class_confidences,
            )
            result_path = self.results_dir / f"{Path(clip_path).stem}.json"
            with open(result_path, 'w') as rf:
                json.dump(asdict(result), rf, indent=2)

    def _classify_clip(self, clip_path: str) -> Optional[str]:
        # Attempt to reuse the existing realtime pipeline for classification
        try:
            import sys, os
            sys.path.append(str(self.training_dir))
            from realtime_inference import ActionRecognizer as TrainingActionRecognizer  # type: ignore
            model = TrainingActionRecognizer(model_path=str(self.training_dir / 'models' / 'action_recognition_model.pth'))
            # Fallback heuristic: use first frame classification
            # Real implementation might run over frames or landmarks time series
            cap = cv2.VideoCapture(clip_path)
            ok, frame = cap.read()
            cap.release()
            if not ok:
                return None
            label, conf, _ = model.process_frame(frame)
            if label in (None, 'no_action', 'collecting_data'):
                return None
            return label
        except Exception:
            return None


