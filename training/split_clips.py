import os
import subprocess
from tqdm import tqdm


def get_video_duration(input_path):
    """Get video duration in seconds using ffprobe."""
    cmd = [
        'ffprobe', 
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_path
    ]
    return float(subprocess.check_output(cmd).decode().strip())


def split_video_into_clips(input_path, output_dir, clip_duration=5):
    """
    Split a video into clips of specified duration using ffmpeg.
    
    Args:
        input_path (str): Path to the input video file
        output_dir (str): Directory to save the output clips
        clip_duration (int): Duration of each clip in seconds
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get video duration
    duration = get_video_duration(input_path)
    
    # Calculate number of clips
    num_clips = int(duration // clip_duration) + (1 if duration % clip_duration > 0 else 0)
    
    # Get the base filename without extension
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # Process each clip
    for clip_idx in tqdm(range(num_clips), desc=f"Splitting {os.path.basename(input_path)}"):
        start_time = clip_idx * clip_duration
        output_path = os.path.join(output_dir, f"{base_name}_{clip_idx+1:03d}.mp4")
        
        # Use ffmpeg to split the video while preserving metadata
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output files
            '-ss', str(start_time),  # Start time
            '-i', input_path,  # Input file
            '-t', str(clip_duration),  # Duration
            '-c', 'copy',  # Copy streams without re-encoding
            '-avoid_negative_ts', '1',  # Avoid negative timestamps
            output_path
        ]
        
        # Run ffmpeg command
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Saved clip to {output_path}")


def main():
    # Define input and output directories
    input_base_dir = "data/original"
    output_dir = "data/clips"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process videos from each category directory
    categories = ["brushing", "flossing", "misc"]
    
    for category in categories:
        category_input_dir = os.path.join(input_base_dir, category)
        
        if not os.path.exists(category_input_dir):
            print(f"Directory {category_input_dir} does not exist, skipping...")
            continue
            
        print(f"\nProcessing {category} videos...")
        
        # Get all video files in the category directory
        video_extensions = ['.mp4', '.mov', '.MOV', '.avi', '.mkv']
        video_files = [f for f in os.listdir(category_input_dir) 
                      if any(f.endswith(ext) for ext in video_extensions)]
        
        if not video_files:
            print(f"No video files found in {category_input_dir}")
            continue
        
        # Process each video
        for video_file in video_files:
            input_path = os.path.join(category_input_dir, video_file)
            
            print(f"Processing {category}/{video_file}...")
            split_video_into_clips(input_path, output_dir)
            print(f"Finished processing {category}/{video_file}")


if __name__ == "__main__":
    main()
