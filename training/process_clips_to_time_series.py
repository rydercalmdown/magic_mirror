import os
import cv2
import numpy as np
import mediapipe as mp
import pandas as pd
from tqdm import tqdm



mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils


def extract_landmarks(results):
    """Extract landmarks from MediaPipe results and flatten them into a single row."""
    landmarks = []
    
    # Face landmarks (if detected)
    if results.face_landmarks:
        face_landmarks = [[lm.x, lm.y, lm.z] for lm in results.face_landmarks.landmark]
        landmarks.extend(np.array(face_landmarks).flatten())
    else:
        # Add zeros if face not detected (468 landmarks * 3 coordinates)
        landmarks.extend(np.zeros(468 * 3))
    
    # Pose landmarks (if detected)
    if results.pose_landmarks:
        pose_landmarks = [[lm.x, lm.y, lm.z] for lm in results.pose_landmarks.landmark]
        landmarks.extend(np.array(pose_landmarks).flatten())
    else:
        # Add zeros if pose not detected (33 landmarks * 3 coordinates)
        landmarks.extend(np.zeros(33 * 3))
    
    # Left hand landmarks (if detected)
    if results.left_hand_landmarks:
        left_hand_landmarks = [[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark]
        landmarks.extend(np.array(left_hand_landmarks).flatten())
    else:
        # Add zeros if left hand not detected (21 landmarks * 3 coordinates)
        landmarks.extend(np.zeros(21 * 3))
    
    # Right hand landmarks (if detected)
    if results.right_hand_landmarks:
        right_hand_landmarks = [[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark]
        landmarks.extend(np.array(right_hand_landmarks).flatten())
    else:
        # Add zeros if right hand not detected (21 landmarks * 3 coordinates)
        landmarks.extend(np.zeros(21 * 3))
    
    return landmarks

def process_video(video_path, output_path):
    """Process a video file and extract landmarks for each frame."""
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Create empty list to store landmarks
    all_landmarks = []
    frame_numbers = []
    
    # Set up MediaPipe Holistic
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as holistic:
        
        # Process each frame
        for frame_idx in tqdm(range(frame_count), desc=f"Processing {os.path.basename(video_path)}"):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert the BGR image to RGB
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the image and get landmarks
            results = holistic.process(image)
            
            # Extract landmarks
            landmarks = extract_landmarks(results)
            
            # Add to our lists
            all_landmarks.append(landmarks)
            frame_numbers.append(frame_idx)
    
    cap.release()
    
    # Create column names for the DataFrame
    column_names = []
    
    # Face landmarks (468 landmarks * 3 coordinates)
    for i in range(468):
        column_names.extend([f'face_{i}_x', f'face_{i}_y', f'face_{i}_z'])
    
    # Pose landmarks (33 landmarks * 3 coordinates)
    for i in range(33):
        column_names.extend([f'pose_{i}_x', f'pose_{i}_y', f'pose_{i}_z'])
    
    # Left hand landmarks (21 landmarks * 3 coordinates)
    for i in range(21):
        column_names.extend([f'left_hand_{i}_x', f'left_hand_{i}_y', f'left_hand_{i}_z'])
    
    # Right hand landmarks (21 landmarks * 3 coordinates)
    for i in range(21):
        column_names.extend([f'right_hand_{i}_x', f'right_hand_{i}_y', f'right_hand_{i}_z'])
    
    # Create DataFrame
    df = pd.DataFrame(all_landmarks, columns=column_names)
    
    # Add frame number and timestamp
    df['frame'] = frame_numbers
    df['timestamp'] = df['frame'] / fps
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    
    return df

def main():
    # Create output directory if it doesn't exist
    input_dir = "data/clips"
    output_dir = "data/series"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all mp4 files in the input directory
    video_files = [f for f in os.listdir(input_dir) if f.endswith('.mp4')]
    
    # Process each video
    for video_file in video_files:
        video_path = os.path.join(input_dir, video_file)
        output_path = os.path.join(output_dir, video_file.replace('.mp4', '.csv'))
        
        print(f"Processing {video_file}...")
        process_video(video_path, output_path)
        print(f"Saved landmarks to {output_path}")

if __name__ == "__main__":
    main()
