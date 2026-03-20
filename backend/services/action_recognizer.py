import os
import sys
import time
from pathlib import Path


class ActionRecognizer:
    """Consumes webcam frames when a person is detected, estimates the current action,
    and marks habits complete after sustained detection using a provided callback.
    """

    def __init__(self, models_dir: Path, sustained_seconds: float = 60.0, mark_habit_completed_fn=None):
        self.models_dir = models_dir
        self.sustained_seconds = sustained_seconds
        self.mark_habit_completed_fn = mark_habit_completed_fn

        self.enabled = True
        self.current_action = None
        self.last_action = None
        self.action_start_time = None
        self.last_emit_time = 0.0
        self.emit_interval = 0.5  # seconds between CURRENT_ACTION emits

        # Try to import training pipeline
        self.pipeline = None
        # Two levels up from backend/services → project root
        self.training_dir = (Path(__file__).resolve().parents[2] / 'training').resolve()
        try:
            sys.path.append(str(self.training_dir))
            from realtime_inference import ActionRecognizer as TrainingActionRecognizer  # type: ignore
            prev_cwd = os.getcwd()
            try:
                os.chdir(self.training_dir)
                self.pipeline = TrainingActionRecognizer(model_path=str(self.models_dir / 'action_recognition_model.pth'))
                print("🤖 ActionRecognizer: Loaded training pipeline from", self.training_dir)
            finally:
                os.chdir(prev_cwd)
        except Exception as e:
            print(f"⚠️ ActionRecognizer: Could not load training pipeline: {e}")
            self.enabled = False

    def process_frame(self, frame_bgr, sio=None):
        if not self.enabled or self.pipeline is None:
            return
        try:
            prev_cwd = os.getcwd()
            os.chdir(self.training_dir)
            action_label, conf, _ = self.pipeline.process_frame(frame_bgr)
            os.chdir(prev_cwd)
            # Only accept confident, non-placeholder labels
            if action_label in (None, 'no_action', 'collecting_data'):
                action_label = None
        except Exception as e:
            print(f"⚠️ ActionRecognizer: Pipeline error: {e}")
            self.enabled = False
            return

        now = time.monotonic()

        # Emit current action periodically for the frontend
        if sio is not None and (action_label != self.current_action or (now - self.last_emit_time) >= self.emit_interval):
            self.current_action = action_label
            self.last_emit_time = now
            print(f"🤖 ActionRecognizer: emitting CURRENT_ACTION: {self.current_action}")
            sio.emit('currentAction', {
                'label': self.current_action
            })

        # Track sustained action window
        if action_label and action_label == self.last_action:
            pass
        else:
            self.action_start_time = now if action_label else None
            self.last_action = action_label

        if self.action_start_time and action_label and self.mark_habit_completed_fn is not None:
            elapsed = now - self.action_start_time
            if elapsed >= self.sustained_seconds:
                habit_name = self._map_action_to_habit(action_label)
                if habit_name:
                    try:
                        updated = self.mark_habit_completed_fn(habit_name)
                        if updated and sio is not None:
                            sio.emit('habitUpdated', {
                                'habits': updated,
                                'completed': habit_name
                            })
                    except Exception as e:
                        print(f"❌ ActionRecognizer: Failed to mark habit complete: {e}")
                # Reset timer to prevent repeated triggers
                self.action_start_time = now

    def _map_action_to_habit(self, action_label: str):
        label = action_label.lower() if action_label else ''
        if 'brush' in label:
            return 'Brush teeth'
        if 'floss' in label:
            return 'Floss'
        return None


