import os
import cv2
import numpy as np
import mediapipe as mp
from tqdm import tqdm
import subprocess
import tempfile
import json

# Initialize MediaPipe solutions
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

def run_ffmpeg_command(cmd, description):
    """Run ffmpeg command with proper error handling."""
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error {description}:")
            print(result.stderr)
            raise Exception(f"ffmpeg command failed: {' '.join(cmd)}")
    except Exception as e:
        print(f"Error {description}: {str(e)}")
        raise

def process_video_with_landmarks(input_path, output_path):
    """
    Process a video file, draw landmarks on each frame, and save as a new video.
    
    Args:
        input_path (str): Path to the input video file
        output_path (str): Path to save the output video with landmarks
    """
    # Create temporary directory for frames
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract frames using ffmpeg
        frame_pattern = os.path.join(temp_dir, 'frame_%04d.jpg')
        extract_cmd = [
            'ffmpeg',
            '-i', input_path,
            '-qscale:v', '2',  # High quality frames
            frame_pattern
        ]
        run_ffmpeg_command(extract_cmd, "extracting frames")
        
        # Get list of extracted frames
        frames = sorted([f for f in os.listdir(temp_dir) if f.startswith('frame_')])
        if not frames:
            raise Exception("No frames were extracted from the video")
        
        # Set up MediaPipe Holistic
        with mp_holistic.Holistic(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5) as holistic:
            
            # Process each frame
            for frame_file in tqdm(frames, desc=f"Processing {os.path.basename(input_path)}"):
                frame_path = os.path.join(temp_dir, frame_file)
                
                # Read frame
                frame = cv2.imread(frame_path)
                if frame is None:
                    continue
                
                # Convert the BGR image to RGB for processing
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process the image and get landmarks
                results = holistic.process(image_rgb)
                
                # Draw landmarks on the frame
                annotated_frame = frame.copy()
                
                # Draw face landmarks
                if results.face_landmarks:
                    mp_drawing.draw_landmarks(
                        annotated_frame, 
                        results.face_landmarks, 
                        mp_holistic.FACEMESH_CONTOURS,
                        mp_drawing.DrawingSpec(color=(80, 110, 10), thickness=1, circle_radius=1),
                        mp_drawing.DrawingSpec(color=(80, 256, 121), thickness=1, circle_radius=1)
                    )
                
                # Draw pose landmarks
                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        annotated_frame, 
                        results.pose_landmarks, 
                        mp_holistic.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
                        mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
                    )
                
                # Draw left hand landmarks
                if results.left_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        annotated_frame, 
                        results.left_hand_landmarks, 
                        mp_holistic.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(121, 22, 76), thickness=2, circle_radius=4),
                        mp_drawing.DrawingSpec(color=(121, 44, 250), thickness=2, circle_radius=2)
                    )
                
                # Draw right hand landmarks
                if results.right_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        annotated_frame, 
                        results.right_hand_landmarks, 
                        mp_holistic.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
                        mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
                    )
                
                # Save the annotated frame
                cv2.imwrite(frame_path, annotated_frame)
        
        # Get video information using ffprobe
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate',
            '-of', 'json',
            input_path
        ]
        probe_output = subprocess.check_output(probe_cmd).decode()
        video_info = json.loads(probe_output)
        stream_info = video_info['streams'][0]
        
        # Calculate fps from the fraction
        fps_parts = stream_info['r_frame_rate'].split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1])
        
        # Create temporary output path
        temp_output = output_path + '.temp.mp4'
        
        # Create output video using ffmpeg
        create_video_cmd = [
            'ffmpeg',
            '-y',
            '-framerate', str(fps),
            '-i', frame_pattern,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'medium',
            '-crf', '23',
            temp_output
        ]
        run_ffmpeg_command(create_video_cmd, "creating output video")
        
        # Copy metadata from original video
        copy_metadata_cmd = [
            'ffmpeg',
            '-y',
            '-i', temp_output,
            '-i', input_path,
            '-map', '0:v',
            '-map_metadata', '1',
            '-c', 'copy',
            output_path
        ]
        run_ffmpeg_command(copy_metadata_cmd, "copying metadata")
        
        # Clean up temporary file
        if os.path.exists(temp_output):
            os.remove(temp_output)
    
    print(f"Saved video with landmarks to {output_path}")

def main():
    # Define input and output directories
    input_dir = "data/clips"
    output_dir = "data/landmarks"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all mp4 files in the input directory
    video_files = [f for f in os.listdir(input_dir) if f.endswith('.mp4')]
    
    # Process each video
    for video_file in video_files:
        input_path = os.path.join(input_dir, video_file)
        output_path = os.path.join(output_dir, video_file)
        
        print(f"Processing {video_file}...")
        try:
            process_video_with_landmarks(input_path, output_path)
            print(f"Finished processing {video_file}")
        except Exception as e:
            print(f"Error processing {video_file}: {str(e)}")
            # Clean up any partial output
            if os.path.exists(output_path):
                os.remove(output_path)

if __name__ == "__main__":
    main()
