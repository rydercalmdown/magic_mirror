#!/usr/bin/env python3
"""
Complete pipeline to process videos from organized directories.
This script runs the entire pipeline: split -> landmarks -> time series
"""

import os
import subprocess
import sys

def run_script(script_name, description):
    """Run a Python script and handle errors."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"Running: {script_name}")
    print(f"{'='*60}")
    
    try:
        # Run without capturing output so we see real-time progress
        result = subprocess.run([sys.executable, script_name], check=True)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error in {description}:")
        print(f"Return code: {e.returncode}")
        return False

def check_directories():
    """Check if required directories exist."""
    required_dirs = [
        "data/original/brushing",
        "data/original/flossing", 
        "data/original/misc"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print("❌ Missing required directories:")
        for dir_path in missing_dirs:
            print(f"   - {dir_path}")
        print("\nPlease create these directories and add your video files.")
        return False
    
    # Check if directories have videos
    has_videos = False
    video_extensions = ['.mp4', '.mov', '.MOV', '.avi', '.mkv']
    for dir_path in required_dirs:
        videos = [f for f in os.listdir(dir_path) 
                 if any(f.endswith(ext) for ext in video_extensions)]
        if videos:
            print(f"✅ Found {len(videos)} videos in {dir_path}")
            has_videos = True
        else:
            print(f"⚠️  No videos found in {dir_path}")
    
    if not has_videos:
        print("❌ No videos found in any directory!")
        return False
    
    return True

def main():
    print("🎬 Magic Mirror Video Processing Pipeline")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("split_clips.py"):
        print("❌ Please run this script from the training directory")
        sys.exit(1)
    
    # Check directories and videos
    if not check_directories():
        sys.exit(1)
    
    # Check how many clips we'll be processing
    clips_dir = "data/clips"
    if os.path.exists(clips_dir):
        clip_files = [f for f in os.listdir(clips_dir) if f.endswith('.mp4')]
        print(f"📊 Found {len(clip_files)} video clips to process")
        if len(clip_files) > 0:
            estimated_time = len(clip_files) * 2  # Rough estimate: 2 minutes per clip
            print(f"⏱️  Estimated processing time: ~{estimated_time} minutes")
            print("💡 The landmarks step is the slowest - it processes every frame!")
        print()
    
    # Run the pipeline
    steps = [
        ("split_clips.py", "Split videos into clips"),
        ("process_clips_to_landmarks_video.py", "Extract landmarks from clips"),
        ("process_clips_to_time_series.py", "Convert landmarks to time series")
    ]
    
    for script, description in steps:
        if not run_script(script, description):
            print(f"\n❌ Pipeline failed at: {description}")
            print("Please fix the error and try again.")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("Next steps:")
    print("1. Run 'make train' to train the model")
    print("2. Run 'make inference' to test real-time detection")
    print("=" * 60)

if __name__ == "__main__":
    main()
