import os
import subprocess
import torch
from pathlib import Path
import shutil
import tempfile
import time

def process_audio_files(vocal_path, beat_path, output_dir):
    """
    Process vocal and beat audio files using Demucs.
    
    Args:
        vocal_path (str): Path to the vocal audio file
        beat_path (str): Path to the beat audio file
        output_dir (str): Directory to store processed results
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Process vocal file
        vocal_output = temp_dir / "vocal_output"
        run_demucs(vocal_path, vocal_output)
        
        # Process beat file
        beat_output = temp_dir / "beat_output"
        run_demucs(beat_path, beat_output)
        
        # Combine the separated components for final output
        combine_results(vocal_output, beat_output, output_dir)
    
    return str(output_dir / "combined.mp3")

def run_demucs(input_file, output_dir):
    """Run Demucs separation on an audio file"""
    try:
        # The model argument can be adjusted based on available models and needs
        # Common options: mdx_extra, mdx, mdx_q, htdemucs_ft, htdemucs
        cmd = [
            "python", "-m", "demucs", 
            "--two-stems=vocals", 
            "-n", "htdemucs",
            "--out", str(output_dir),
            str(input_file)
        ]
        
        # Run the command
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error running Demucs: {e}")
        raise

def combine_results(vocal_output, beat_output, final_output):
    """
    Combine the separated components into a final output.
    This is a simplified example - you'd want to customize based on your needs.
    """
    # Find the separated files
    # The actual paths will depend on Demucs output structure
    # This is a simplified approach - you may need to adjust paths
    vocal_stems = list(vocal_output.glob("**/vocals.wav"))
    beat_stems = list(beat_output.glob("**/no_vocals.wav"))
    
    if not vocal_stems or not beat_stems:
        raise FileNotFoundError("Could not find separated audio components")
    
    vocal_file = vocal_stems[0]
    instrumental_file = beat_stems[0]
    
    # Example: Combine using ffmpeg
    output_file = final_output / "combined.mp3"
    
    # This is a simple mix - you might want more sophisticated audio processing
    cmd = [
        "ffmpeg",
        "-i", str(vocal_file),
        "-i", str(instrumental_file),
        "-filter_complex", "amix=inputs=2:duration=longest:dropout_transition=2",
        "-b:a", "192k",
        str(output_file)
    ]
    
    subprocess.run(cmd, check=True)
    
    return str(output_file)