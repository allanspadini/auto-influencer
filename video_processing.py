import numpy as np
from moviepy import VideoFileClip, concatenate_videoclips
import imageio_ffmpeg
import subprocess

def remove_silence(input_path: str, output_path: str, threshold_db: float = -40.0, min_duration: float = 0.5, padding: float = 0.1):
    """
    Removes silent sections from a video.
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        threshold_db: Decibel threshold for silence (relative to max amplitude)
        min_duration: Minimum duration of silence to cut (in seconds)
        padding: Padding to add around keeping segments (in seconds)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # try:
    clip = VideoFileClip(input_path)
    
    # Audio analysis
    # Iterate over audio in chunks
    chunk_duration = 0.1 # 100ms chunks
    if clip.audio is None:
        raise ValueError("Video has no audio.")

    fps = clip.audio.fps
    chunk_size = int(fps * chunk_duration)
    
    # Get max volume for reference if needed, or use absolute
    # For simplicity, we'll check if RMS < 10^(threshold_db/20)
    # But moviepy audio is usually -1.0 to 1.0. 
    # 0dB is 1.0. -40dB is 0.01.
    
    limit = 10 ** (threshold_db / 20)
    
    keep_intervals = []
    is_silent = True
    current_start = 0.0
    
    # We will collect "loud" intervals
    loud_intervals = []
    in_loud = False
    start_loud = 0.0
    
    # Analyze audio
    # using iter_chunks is memory efficient
    time_counter = 0.0
    
    # We need a list of bools: is_loud
    is_loud_list = []
    
    for chunk in clip.audio.iter_chunks(chunksize=chunk_size):
        # Check max amplitude in chunk (stereo or mono)
        if chunk.ndim == 2:
            max_val = np.max(np.abs(chunk))
        else:
            max_val = np.max(np.abs(chunk))
            
        is_loud_chunk = max_val > limit
        is_loud_list.append(is_loud_chunk)
        
    # Refine intervals
    # Group consecutive loud chunks
    
    num_chunks = len(is_loud_list)
    
    # Helper to convert chunk index to time
    def idx_to_time(i):
        return i * chunk_duration
        
    current_loud_start = None
    
    ranges = [] # (start, end) of loud parts
    
    for i, is_loud in enumerate(is_loud_list):
        if is_loud:
            if current_loud_start is None:
                current_loud_start = idx_to_time(i)
        else:
            if current_loud_start is not None:
                # End of loud segment
                end_time = idx_to_time(i)
                ranges.append([current_loud_start, end_time])
                current_loud_start = None
    
    # Handle case where it ends loud
    if current_loud_start is not None:
        ranges.append([current_loud_start, idx_to_time(num_chunks)])
        
    if not ranges:
        # All silent? Return original or empty?
        # Let's return original to be safe
        print("No loud sections found. Returning original.")
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        return True

    # Merge close ranges (less than min_duration silence)
    merged_ranges = []
    if ranges:
        curr_start, curr_end = ranges[0]
        
        for next_start, next_end in ranges[1:]:
            # If silence between is small, merge
            if next_start - curr_end < min_duration:
                curr_end = next_end # Extend current
            else:
                merged_ranges.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_ranges.append((curr_start, curr_end))
    
    # Apply padding
    padded_ranges = []
    duration = clip.duration
    
    for start, end in merged_ranges:
        s = max(0, start - padding)
        e = min(duration, end + padding)
        # Avoid overlaps if padding made them overlap
        if padded_ranges and s < padded_ranges[-1][1]:
            padded_ranges[-1] = (padded_ranges[-1][0], max(padded_ranges[-1][1], e))
        else:
            padded_ranges.append((s, e))
            
    # Create subclips
    clips = [clip.subclipped(s, e) for s, e in padded_ranges]
    
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    clip.close()
    final_clip.close()
    return True
    
    # except Exception as e:
    #     print(f"Error removing silence: {e}")
    #     return False

def adjust_volume(input_path: str, output_path: str, volume_factor: float):
    """
    Adjusts the volume of a video.
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        volume_factor: Multiplier for volume (e.g., 1.5 for 150%)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # ffmpeg -i input.mp4 -filter:a "volume=1.5" -c:v copy output.mp4
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y",
            "-i", input_path,
            "-filter:a", f"volume={volume_factor}",
            "-c:v", "copy", # Copy video stream (fast)
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"Error adjusting volume: {e}")
        raise e

def remove_segment(input_path: str, output_path: str, start: float, end: float):
    """
    Removes a specific segment (start to end) from the video.
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        start: Start time of the segment to remove (seconds)
        end: End time of the segment to remove (seconds)
    """
    try:
        clip = VideoFileClip(input_path)
        duration = clip.duration
        
        # Validate logic
        start = max(0, start)
        end = min(duration, end)
        if start >= end:
            raise ValueError("Start time must be less than end time.")
            
        clips = []
        
        # Part before the cut
        if start > 0:
            clips.append(clip.subclipped(0, start))
            
        # Part after the cut
        if end < duration:
            clips.append(clip.subclipped(end, duration))
            
        if not clips:
             # Removed everything?
             raise ValueError("The cut removes the entire video.")
             
        final_clip = concatenate_videoclips(clips)
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        clip.close()
        final_clip.close()
        return True
    except Exception as e:
        print(f"Error removing segment: {e}")
        raise e
