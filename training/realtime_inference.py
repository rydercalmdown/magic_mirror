import cv2
import numpy as np
import mediapipe as mp
import torch
import torch.nn as nn
import pickle
from collections import deque
import time
import os

class TinyLSTM(nn.Module):
    """Tiny LSTM model optimized for Raspberry Pi CPU inference."""
    def __init__(self, input_size, hidden_size1=16, hidden_size2=8, num_classes=3):
        super(TinyLSTM, self).__init__()
        
        self.lstm1 = nn.LSTM(input_size, hidden_size1, batch_first=True)
        self.dropout1 = nn.Dropout(0.2)
        
        self.lstm2 = nn.LSTM(hidden_size1, hidden_size2, batch_first=True)
        self.dropout2 = nn.Dropout(0.2)
        
        self.fc1 = nn.Linear(hidden_size2, 32)
        self.dropout3 = nn.Dropout(0.2)
        self.fc2 = nn.Linear(32, num_classes)
        
        self.relu = nn.ReLU()
    
    def forward(self, x):
        # First LSTM layer
        lstm1_out, _ = self.lstm1(x)
        lstm1_out = self.dropout1(lstm1_out)
        
        # Second LSTM layer
        lstm2_out, _ = self.lstm2(lstm1_out)
        lstm2_out = self.dropout2(lstm2_out)
        
        # Take the last output
        last_output = lstm2_out[:, -1, :]
        
        # Fully connected layers
        fc1_out = self.relu(self.fc1(last_output))
        fc1_out = self.dropout3(fc1_out)
        output = self.fc2(fc1_out)
        
        return output

class ActionRecognizer:
    def __init__(self, model_path="models/action_recognition_model.pth"):
        self.device = torch.device('cpu')  # Force CPU for Raspberry Pi
        
        # Load model info
        with open("models/model_info.pkl", "rb") as f:
            self.model_info = pickle.load(f)
        
        # Load preprocessors
        with open("models/label_encoder.pkl", "rb") as f:
            self.label_encoder = pickle.load(f)
        
        with open("models/scaler.pkl", "rb") as f:
            self.scaler = pickle.load(f)
        
        # Initialize model
        self.model = TinyLSTM(
            input_size=self.model_info["input_size"],
            num_classes=self.model_info["num_classes"]
        ).to(self.device)
        
        # Load trained weights
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        
        self.sequence_length = self.model_info["sequence_length"]
        self.classes = self.model_info["classes"]
        
        # Initialize MediaPipe
        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=1,  # Reduced for speed
            enable_segmentation=False,
            refine_face_landmarks=False
        )
        
        # Buffer for landmarks
        self.landmark_buffer = deque(maxlen=self.sequence_length)
        
        # Prediction smoothing
        self.prediction_buffer = deque(maxlen=15)  # Longer buffer for smoothing
        self.confidence_threshold = 0.95  # 95% confidence threshold
        
        print(f"Model loaded. Classes: {self.classes}")
        print(f"Sequence length: {self.sequence_length}")
        print(f"Using device: {self.device}")
    
    def extract_landmarks(self, results):
        """Extract landmarks from MediaPipe results."""
        landmarks = []
        
        # Face landmarks (if detected)
        if results.face_landmarks:
            face_landmarks = [[lm.x, lm.y, lm.z] for lm in results.face_landmarks.landmark]
            landmarks.extend(np.array(face_landmarks).flatten())
        else:
            landmarks.extend(np.zeros(468 * 3))
        
        # Pose landmarks (if detected)
        if results.pose_landmarks:
            pose_landmarks = [[lm.x, lm.y, lm.z] for lm in results.pose_landmarks.landmark]
            landmarks.extend(np.array(pose_landmarks).flatten())
        else:
            landmarks.extend(np.zeros(33 * 3))
        
        # Left hand landmarks (if detected)
        if results.left_hand_landmarks:
            left_hand_landmarks = [[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark]
            landmarks.extend(np.array(left_hand_landmarks).flatten())
        else:
            landmarks.extend(np.zeros(21 * 3))
        
        # Right hand landmarks (if detected)
        if results.right_hand_landmarks:
            right_hand_landmarks = [[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark]
            landmarks.extend(np.array(right_hand_landmarks).flatten())
        else:
            landmarks.extend(np.zeros(21 * 3))
        
        return np.array(landmarks)
    
    def predict_action(self):
        """Predict action from current buffer."""
        if len(self.landmark_buffer) < self.sequence_length:
            return "collecting_data", 0.0
        
        # Prepare sequence
        sequence = np.array(list(self.landmark_buffer))
        
        # Handle feature mismatch by padding or truncating
        expected_features = self.scaler.n_features_in_
        current_features = sequence.shape[-1]
        
        if current_features < expected_features:
            # Pad with zeros if we have fewer features
            padding = np.zeros((sequence.shape[0], expected_features - current_features))
            sequence = np.concatenate([sequence, padding], axis=1)
        elif current_features > expected_features:
            # Truncate if we have more features
            sequence = sequence[:, :expected_features]
        
        sequence_scaled = self.scaler.transform(sequence.reshape(-1, sequence.shape[-1]))
        sequence_scaled = sequence_scaled.reshape(1, self.sequence_length, -1)
        
        # Convert to tensor
        sequence_tensor = torch.FloatTensor(sequence_scaled).to(self.device)
        
        # Predict
        with torch.no_grad():
            prediction = self.model(sequence_tensor)
            probabilities = torch.softmax(prediction, dim=1)
            confidence, predicted_class_idx = torch.max(probabilities, 1)
            
            predicted_class = self.label_encoder.inverse_transform([predicted_class_idx.item()])[0]
            confidence_score = confidence.item()
        
        # Smooth predictions with confidence threshold
        self.prediction_buffer.append((predicted_class_idx.item(), confidence_score))
        
        if len(self.prediction_buffer) >= 10:  # Need more predictions for smoothing
            # Get recent high-confidence predictions
            recent_predictions = list(self.prediction_buffer)[-10:]
            high_conf_predictions = [(pred, conf) for pred, conf in recent_predictions if conf >= self.confidence_threshold]
            
            if len(high_conf_predictions) >= 7:  # Need 7/10 high-confidence predictions
                # Use majority vote among high-confidence predictions
                pred_classes = [pred for pred, conf in high_conf_predictions]
                most_common = max(set(pred_classes), key=pred_classes.count)
                smoothed_class = self.label_encoder.inverse_transform([most_common])[0]
                avg_confidence = np.mean([conf for pred, conf in high_conf_predictions])
                return smoothed_class, avg_confidence
        
        # If not enough high-confidence predictions, return "no_action"
        return "no_action", confidence_score
    
    def get_raw_predictions(self):
        """Get raw prediction probabilities for all classes."""
        if len(self.landmark_buffer) < self.sequence_length:
            return None
        
        # Prepare sequence
        sequence = np.array(list(self.landmark_buffer))
        
        # Handle feature mismatch by padding or truncating
        expected_features = self.scaler.n_features_in_
        current_features = sequence.shape[-1]
        
        if current_features < expected_features:
            # Pad with zeros if we have fewer features
            padding = np.zeros((sequence.shape[0], expected_features - current_features))
            sequence = np.concatenate([sequence, padding], axis=1)
        elif current_features > expected_features:
            # Truncate if we have more features
            sequence = sequence[:, :expected_features]
        
        sequence_scaled = self.scaler.transform(sequence.reshape(-1, sequence.shape[-1]))
        sequence_scaled = sequence_scaled.reshape(1, self.sequence_length, -1)
        
        # Convert to tensor
        sequence_tensor = torch.FloatTensor(sequence_scaled).to(self.device)
        
        # Predict
        with torch.no_grad():
            prediction = self.model(sequence_tensor)
            probabilities = torch.softmax(prediction, dim=1)
            return probabilities[0].cpu().numpy()
    
    def draw_confidence_bars(self, frame):
        """Draw confidence bars for all classes."""
        probabilities = self.get_raw_predictions()
        if probabilities is None:
            return
        
        # Bar chart parameters
        bar_width = 60
        bar_height = 200
        start_x = frame.shape[1] - 200
        start_y = 50
        spacing = 80
        
        # Colors for each class
        colors = {
            'brushing': (0, 255, 0),    # Green
            'flossing': (255, 0, 0),    # Blue  
            'no_action': (0, 0, 255)    # Red
        }
        
        # Draw bars for each class
        for i, class_name in enumerate(self.classes):
            confidence = probabilities[i]
            bar_fill_height = int(bar_height * confidence)
            
            # Bar background (gray)
            cv2.rectangle(frame, 
                         (start_x + i * spacing, start_y + bar_height - bar_fill_height),
                         (start_x + i * spacing + bar_width, start_y + bar_height),
                         colors.get(class_name, (128, 128, 128)), -1)
            
            # Bar outline (white)
            cv2.rectangle(frame, 
                         (start_x + i * spacing, start_y),
                         (start_x + i * spacing + bar_width, start_y + bar_height),
                         (255, 255, 255), 2)
            
            # Class name and confidence
            cv2.putText(frame, class_name, 
                       (start_x + i * spacing, start_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"{confidence:.2f}", 
                       (start_x + i * spacing, start_y + bar_height + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw threshold line
        threshold_y = start_y + bar_height - int(bar_height * self.confidence_threshold)
        cv2.line(frame, 
                (start_x - 10, threshold_y), 
                (start_x + len(self.classes) * spacing + bar_width + 10, threshold_y), 
                (255, 255, 0), 2)  # Yellow threshold line
        cv2.putText(frame, "95%", 
                   (start_x - 50, threshold_y - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    
    def process_frame(self, frame):
        """Process a single frame and return prediction."""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.holistic.process(rgb_frame)
        
        # Extract landmarks
        landmarks = self.extract_landmarks(results)
        self.landmark_buffer.append(landmarks)
        
        # Predict action
        action, confidence = self.predict_action()
        
        return action, confidence, results

def main():
    # Check if model exists
    if not os.path.exists("models/action_recognition_model.pth"):
        print("Model not found! Please run 'make train' first to train the model.")
        return
    
    # Initialize recognizer
    print("Initializing action recognizer...")
    recognizer = ActionRecognizer()
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("Starting real-time action recognition...")
    print("Press 'q' to quit, 's' to save screenshot")
    
    fps_counter = 0
    start_time = time.time()
    last_fps_time = start_time
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        action, confidence, results = recognizer.process_frame(frame)
        
        # Calculate FPS
        fps_counter += 1
        current_time = time.time()
        if current_time - last_fps_time >= 1.0:  # Update FPS every second
            fps = fps_counter / (current_time - last_fps_time)
            last_fps_time = current_time
            fps_counter = 0
        
        # Draw results with color coding based on confidence
        color = (0, 255, 0) if confidence >= 0.95 else (0, 255, 255) if confidence >= 0.8 else (0, 0, 255)
        cv2.putText(frame, f"Action: {action}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"Confidence: {confidence:.2f}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"Threshold: 0.95", (10, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw buffer status
        buffer_status = f"Buffer: {len(recognizer.landmark_buffer)}/{recognizer.sequence_length}"
        cv2.putText(frame, buffer_status, (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Draw confidence bar chart (shows raw real-time predictions)
        recognizer.draw_confidence_bars(frame)
        
        # Also show raw prediction info
        raw_probs = recognizer.get_raw_predictions()
        if raw_probs is not None:
            max_class_idx = np.argmax(raw_probs)
            max_class = recognizer.classes[max_class_idx]
            max_confidence = raw_probs[max_class_idx]
            cv2.putText(frame, f"Raw: {max_class} ({max_confidence:.2f})", (10, 190), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show smoothing status
            smoothing_status = f"Smoothing: {len(recognizer.prediction_buffer)}/15"
            cv2.putText(frame, smoothing_status, (10, 230), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw landmarks (optional, for debugging)
        if results.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, results.pose_landmarks, mp.solutions.holistic.POSE_CONNECTIONS
            )
        
        if results.left_hand_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, results.left_hand_landmarks, mp.solutions.holistic.HAND_CONNECTIONS
            )
        
        if results.right_hand_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, results.right_hand_landmarks, mp.solutions.holistic.HAND_CONNECTIONS
            )
        
        # Show frame
        cv2.imshow('Action Recognition', frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save screenshot
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Screenshot saved as {filename}")
    
    cap.release()
    cv2.destroyAllWindows()
    print("Action recognition stopped.")

if __name__ == "__main__":
    main()
