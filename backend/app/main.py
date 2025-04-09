import os
import shutil
import tempfile
import torch
import traceback
import librosa
import numpy as np
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio
from demucs.apply import apply_model
import soundfile as sf

app = FastAPI()

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a folder for storing output files
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Create a folder for storing processing files
PROCESSING_DIR = os.path.join(os.path.dirname(__file__), "processing")
os.makedirs(PROCESSING_DIR, exist_ok=True)

def calculate_key_semitones(source_key: str, target_key: str) -> int:
    """
    Calculate the number of semitones to transpose from source key to target key.
    
    Args:
        source_key: The original key
        target_key: The target key
        
    Returns:
        Number of semitones to transpose (positive or negative)
    """
    # Map of musical keys to their semitone positions
    key_to_semitone = {
        'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 
        'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11,
        'Cm': 12, 'C#m': 13, 'Dm': 14, 'D#m': 15, 'Em': 16, 'Fm': 17,
        'F#m': 18, 'Gm': 19, 'G#m': 20, 'Am': 21, 'A#m': 22, 'Bm': 23
    }
    
    # Get semitone positions
    source_pos = key_to_semitone.get(source_key)
    target_pos = key_to_semitone.get(target_key)
    
    if source_pos is None or target_pos is None:
        raise ValueError(f"Invalid key: {source_key if source_pos is None else target_key}")
    
    # Calculate the shortest distance to transpose
    if source_pos < 12 and target_pos < 12:  # Both major
        semitones = (target_pos - source_pos) % 12
        if semitones > 6:
            semitones -= 12
    elif source_pos >= 12 and target_pos >= 12:  # Both minor
        semitones = (target_pos - source_pos) % 12
        if semitones > 6:
            semitones -= 12
    else:
        # Different modes (major/minor), use relative keys
        if source_pos < 12:  # Source is major
            rel_minor = (source_pos + 9) % 12 + 12
            semitones = (target_pos - rel_minor) % 12
        else:  # Source is minor
            rel_major = (source_pos - 9) % 12
            semitones = (target_pos - rel_major) % 12
        
        if semitones > 6:
            semitones -= 12
    
    return semitones

def transpose_audio(y, sr, n_steps):
    """
    Transpose audio by n_steps semitones.
    
    Args:
        y: Audio time series
        sr: Sample rate
        n_steps: Number of semitones to transpose
        
    Returns:
        Transposed audio time series
    """
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=n_steps)

def adjust_tempo(y, sr, tempo_ratio):
    """
    Adjust the tempo of an audio signal.
    
    Args:
        y: Audio time series
        sr: Sample rate
        tempo_ratio: Ratio of target tempo to original tempo (target_tempo / original_tempo)
        
    Returns:
        Time-stretched audio time series
    """
    return librosa.effects.time_stretch(y, rate=tempo_ratio)

def find_best_tempo_ratio(source_bpm, target_bpm):
    """
    Find the best tempo ratio to adjust source_bpm to target_bpm.
    
    Instead of slowing down, this function will attempt to find a multiple
    of target_bpm that is close to source_bpm, or vice versa.
    
    Args:
        source_bpm: Original BPM
        target_bpm: Target BPM
        
    Returns:
        Optimal tempo ratio to maintain best quality
    """
    # Direct ratio (might be slowing down)
    direct_ratio = target_bpm / source_bpm
    
    # If we're already speeding up, just use the direct ratio
    if direct_ratio >= 1.0:
        return direct_ratio
    
    # Try to find multiples of target_bpm that are close to source_bpm
    multiples = []
    for i in range(1, 5):  # Try up to 4x multiplier
        ratio = (target_bpm * i) / source_bpm
        if ratio >= 0.8:  # Don't slow down more than 20%
            multiples.append((ratio, abs(1 - ratio)))
    
    # Try to find fractions of source_bpm that are close to target_bpm
    for i in range(2, 5):  # Try 1/2, 1/3, 1/4
        ratio = target_bpm / (source_bpm / i)
        if ratio >= 0.8:  # Don't slow down more than 20%
            multiples.append((ratio, abs(1 - ratio)))
    
    # If we found any good multiples, pick the one closest to 1.0 (least change)
    if multiples:
        multiples.sort(key=lambda x: x[1])  # Sort by closeness to 1.0
        return multiples[0][0]
    
    # Fall back to direct ratio if no good multiple found
    return direct_ratio

def shift_audio_in_time(audio, sr, offset_beats, bpm):
    """
    Shift audio forward or backward in time by a specified number of beats
    
    Args:
        audio: Audio time series
        sr: Sample rate
        offset_beats: Number of beats to shift (positive = forward, negative = backward)
        bpm: Beats per minute
    
    Returns:
        Shifted audio time series
    """
    # Calculate beat duration in seconds
    beat_duration = 60.0 / bpm  # seconds per beat
    
    # Calculate shift in samples
    offset_samples = int(offset_beats * beat_duration * sr)
    
    # Create output array with same shape as input, but filled with zeros
    output = np.zeros_like(audio)
    
    if offset_samples > 0:
        # Shift forward (delay) - move samples later in time
        output[..., offset_samples:] = audio[..., :-offset_samples]
    elif offset_samples < 0:
        # Shift backward - move samples earlier in time
        offset_samples = abs(offset_samples)
        output[..., :-offset_samples] = audio[..., offset_samples:]
    else:
        # No shift
        output = audio.copy()
        
    return output

def normalize_audio(audio, target_dB=-20):
    """
    Normalize audio to a target dB level
    
    Args:
        audio: Audio time series (numpy array)
        target_dB: Target dB level (default: -20dB which is good for mixing)
    
    Returns:
        Normalized audio time series
    """
    # Calculate current RMS (root mean square) energy
    rms = np.sqrt(np.mean(audio**2))
    
    # Convert target dB to linear gain
    target_rms = 10**(target_dB/20.0)
    
    # Calculate gain needed
    gain = target_rms / (rms + 1e-9)  # Adding small value to prevent division by zero
    
    print(f"Normalizing audio: current RMS = {20*np.log10(rms+1e-9):.2f} dB, gain = {20*np.log10(gain):.2f} dB")
    
    # Apply gain
    return audio * gain

@app.post("/prepare-audio")
async def prepare_audio(
    vocal_file: UploadFile = File(...),
    beat_file: UploadFile = File(...),
    vocal_key: Optional[str] = Form(None),
    beat_key: Optional[str] = Form(None), 
    vocal_bpm: Optional[float] = Form(None),
    beat_bpm: Optional[float] = Form(None)
):
    # Create a unique processing ID
    processing_id = str(uuid.uuid4())
    processing_dir = os.path.join(PROCESSING_DIR, processing_id)
    os.makedirs(processing_dir, exist_ok=True)
    
    try:
        # Save uploaded files with correct extensions
        vocal_extension = os.path.splitext(vocal_file.filename)[1] or '.mp3'
        beat_extension = os.path.splitext(beat_file.filename)[1] or '.mp3'
        
        vocal_path = os.path.join(processing_dir, f'vocal{vocal_extension}')
        beat_path = os.path.join(processing_dir, f'beat{beat_extension}')
        
        # Save uploaded files
        with open(vocal_path, 'wb') as f:
            content = await vocal_file.read()
            f.write(content)
        await vocal_file.seek(0)
        
        with open(beat_path, 'wb') as f:
            content = await beat_file.read()
            f.write(content)
        await beat_file.seek(0)
        
        print(f"Files saved to: {vocal_path} and {beat_path}")
        
        # Convert to float
        vocal_bpm = float(vocal_bpm)
        beat_bpm = float(beat_bpm)
        
        # Initialize adjusted BPM to the vocal BPM
        adjusted_beat_bpm = vocal_bpm

        # Process the beat track to match vocal parameters
        if vocal_key != beat_key or abs(vocal_bpm - beat_bpm) > 1.0:
            print(f"Adjusting beat track from key={beat_key}, bpm={beat_bpm} to key={vocal_key}, bpm={vocal_bpm}")
            beat_audio_data, beat_sr = librosa.load(beat_path, sr=None)
            processed_beat_path = os.path.join(processing_dir, 'processed_beat.wav')
            
            # Determine if we need to transpose or adjust tempo
            needs_transposition = vocal_key != beat_key
            needs_tempo_adjustment = abs(vocal_bpm - beat_bpm) > 1.0
            
            # Calculate optimal tempo ratio using our new function
            tempo_ratio = find_best_tempo_ratio(beat_bpm, vocal_bpm) if needs_tempo_adjustment else 1.0
            
            # Calculate final BPM after adjustment
            adjusted_beat_bpm = beat_bpm * tempo_ratio
            print(f"Using tempo ratio: {tempo_ratio:.4f}, resulting in BPM: {adjusted_beat_bpm:.2f}")
            
            # Continue with the existing logic for transposition and tempo adjustment
            if needs_transposition:
                try:
                    n_semitones = calculate_key_semitones(beat_key, vocal_key)
                    print(f"Transposing from {beat_key} to {vocal_key} ({n_semitones} semitones)")
                    
                    # For large transpositions, it's better to transpose first
                    if abs(n_semitones) > 3 or not needs_tempo_adjustment:
                        print("Transposing first...")
                        beat_audio_data = transpose_audio(beat_audio_data, beat_sr, n_semitones)
                        
                        if needs_tempo_adjustment:
                            print(f"Then adjusting tempo with ratio: {tempo_ratio:.4f}")
                            beat_audio_data = adjust_tempo(beat_audio_data, beat_sr, tempo_ratio)
                    else:
                        # For small transpositions with tempo changes, adjust tempo first
                        if needs_tempo_adjustment:
                            print(f"Adjusting tempo first with ratio: {tempo_ratio:.4f}")
                            beat_audio_data = adjust_tempo(beat_audio_data, beat_sr, tempo_ratio)
                        
                        print(f"Then transposing {n_semitones} semitones")
                        beat_audio_data = transpose_audio(beat_audio_data, beat_sr, n_semitones)
                except Exception as e:
                    print(f"Error during transposition: {str(e)}")
                    # Continue with tempo adjustment only if transposition fails
                    if needs_tempo_adjustment:
                        print(f"Falling back to tempo adjustment only with ratio: {tempo_ratio:.4f}")
                        beat_audio_data = adjust_tempo(beat_audio_data, beat_sr, tempo_ratio)
            elif needs_tempo_adjustment:
                print(f"Adjusting tempo with ratio: {tempo_ratio:.4f}")
                beat_audio_data = adjust_tempo(beat_audio_data, beat_sr, tempo_ratio)
            
            # Save the processed beat
            sf.write(processed_beat_path, beat_audio_data, beat_sr)
            print(f"Processed beat saved to {processed_beat_path}")
            beat_path = processed_beat_path
        
        # Load Demucs model and process files
        print("Loading Demucs model...")
        model = get_model('htdemucs')
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        
        # NOW the model is available, so we can create the metadata
        # Save metadata
        metadata = {
            "processing_id": processing_id,
            "vocal_key": vocal_key,
            "vocal_bpm": vocal_bpm,
            "beat_key": beat_key,
            "beat_bpm": beat_bpm,
            "final_key": vocal_key,
            "final_bpm": adjusted_beat_bpm,  # Use the adjusted BPM
            "sample_rate": model.samplerate,
            "offset_beats": 0.0  # Start with no offset
        }
        
        # Process vocal file - extract vocals
        vocal_audio = AudioFile(vocal_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
        if vocal_audio.dim() == 2:
            vocal_audio = vocal_audio.unsqueeze(0)

        vocal_estimates = apply_model(model, vocal_audio, device=device)[0]
        vocal_stem_idx = model.sources.index('vocals')
        vocal_stem = vocal_estimates[vocal_stem_idx]

        # Process beat file - get instrumental
        beat_audio = AudioFile(beat_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
        if beat_audio.dim() == 2:
            beat_audio = beat_audio.unsqueeze(0)

        beat_estimates = apply_model(model, beat_audio, device=device)[0]
        instrumental_sources = [i for i, name in enumerate(model.sources) if name != 'vocals']
        instrumental_stems = [beat_estimates[i] for i in instrumental_sources]
        instrumental = sum(instrumental_stems)

        # Convert tensors to numpy arrays for normalization
        vocal_np = vocal_stem.cpu().numpy()
        instrumental_np = instrumental.cpu().numpy()

        # Normalize both stems to a consistent level
        print("Normalizing vocal and instrumental stems...")
        vocal_np_normalized = normalize_audio(vocal_np, target_dB=-24)
        instrumental_np_normalized = normalize_audio(instrumental_np, target_dB=-24)  # Slightly quieter for instruments

        # Convert back to torch tensors
        vocal_stem = torch.from_numpy(vocal_np_normalized)
        instrumental = torch.from_numpy(instrumental_np_normalized)

        # Save the extracted stems
        vocal_stem_path = os.path.join(processing_dir, 'vocal_stem.pt')
        instrumental_path = os.path.join(processing_dir, 'instrumental.pt')
        
        # Save as PyTorch tensors
        torch.save(vocal_stem, vocal_stem_path)
        torch.save(instrumental, instrumental_path)
        
        metadata_path = os.path.join(processing_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        # Create a preview with no offset
        preview_path = os.path.join(processing_dir, 'preview.mp3')
        min_length = min(vocal_stem.shape[-1], instrumental.shape[-1])
        vocal_stem_preview = vocal_stem[..., :min_length]
        instrumental_preview = instrumental[..., :min_length]
        preview_mix = vocal_stem_preview + instrumental_preview
        save_audio(preview_mix, preview_path, model.samplerate)
        
        return {
            "success": True,
            "processing_id": processing_id,
            "preview_url": f"/preview/{processing_id}",
            "vocal_key": vocal_key,
            "vocal_bpm": vocal_bpm,
            "beat_key": beat_key,
            "beat_bpm": beat_bpm,
            "offset_beats": 0.0
        }
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error preparing audio: {str(e)}")
        print(error_details)
        
        # Clean up the processing directory on error
        if os.path.exists(processing_dir):
            shutil.rmtree(processing_dir)
            
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "details": error_details}
        )  

@app.get("/preview/{processing_id}")
async def get_preview(processing_id: str):
    """Serve the preview audio file"""
    preview_path = os.path.join(PROCESSING_DIR, processing_id, 'preview.mp3')
    if not os.path.exists(preview_path):
        raise HTTPException(status_code=404, detail="Preview not found")
        
    return FileResponse(
        preview_path,
        media_type='audio/mpeg',
        headers={
            "Content-Disposition": "inline; filename=preview.mp3",
            "Accept-Ranges": "bytes"
        }
    )

@app.post("/adjust-offset")
async def adjust_offset(
    processing_id: str = Form(...),
    offset_beats: float = Form(...)
):
    """Adjust the vocal offset and generate a new preview"""
    processing_dir = os.path.join(PROCESSING_DIR, processing_id)
    if not os.path.exists(processing_dir):
        raise HTTPException(status_code=404, detail="Processing session not found")
    
    try:
        # Load metadata
        metadata_path = os.path.join(processing_dir, 'metadata.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            
        # Load stems
        vocal_stem = torch.load(os.path.join(processing_dir, 'vocal_stem.pt'))
        instrumental = torch.load(os.path.join(processing_dir, 'instrumental.pt'))
        
        # Convert vocal stem to numpy for processing
        vocal_np = vocal_stem.cpu().numpy()

        # Shift vocal in time according to offset
        vocal_bpm = metadata["vocal_bpm"]
        shifted_vocal_np = shift_audio_in_time(vocal_np, metadata["sample_rate"], offset_beats, vocal_bpm)

        # Normalize the shifted vocals
        shifted_vocal_np = normalize_audio(shifted_vocal_np, target_dB=-24)

        # Convert back to torch tensor
        shifted_vocal = torch.from_numpy(shifted_vocal_np)
        
        # Generate new preview
        preview_path = os.path.join(processing_dir, 'preview.mp3')
        min_length = min(shifted_vocal.shape[-1], instrumental.shape[-1])
        vocal_preview = shifted_vocal[..., :min_length]
        instrumental_preview = instrumental[..., :min_length]
        preview_mix = vocal_preview + instrumental_preview
        save_audio(preview_mix, preview_path, metadata["sample_rate"])
        
        # Update metadata
        metadata["offset_beats"] = float(offset_beats)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
            
        return {
            "success": True,
            "processing_id": processing_id,
            "preview_url": f"/preview/{processing_id}",
            "offset_beats": float(offset_beats)
        }
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error adjusting offset: {str(e)}")
        print(error_details)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "details": error_details}
        )

@app.post("/finalize-mix")
async def finalize_mix(
    processing_id: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    """Create the final mix with the current offset setting"""
    processing_dir = os.path.join(PROCESSING_DIR, processing_id)
    if not os.path.exists(processing_dir):
        raise HTTPException(status_code=404, detail="Processing session not found")
    
    try:
        # Load metadata
        metadata_path = os.path.join(processing_dir, 'metadata.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            
        # Create output filename
        output_filename = f"processed_mix_{processing_id}.mp3"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Load stems
        vocal_stem = torch.load(os.path.join(processing_dir, 'vocal_stem.pt'))
        instrumental = torch.load(os.path.join(processing_dir, 'instrumental.pt'))
        
        # Apply offset if needed
        if metadata["offset_beats"] != 0:
            vocal_np = vocal_stem.cpu().numpy()
            shifted_vocal_np = shift_audio_in_time(
                vocal_np, metadata["sample_rate"], 
                metadata["offset_beats"], metadata["vocal_bpm"]
            )
            vocal_stem = torch.from_numpy(shifted_vocal_np)
        
        # Mix and save
        min_length = min(vocal_stem.shape[-1], instrumental.shape[-1])
        vocal_final = vocal_stem[..., :min_length]
        instrumental_final = instrumental[..., :min_length]
        final_mix = vocal_final + instrumental_final
        save_audio(final_mix, output_path, metadata["sample_rate"])
        
        # Schedule cleanup in the background
        if background_tasks:
            background_tasks.add_task(shutil.rmtree, processing_dir)
        
        # Return the processed file
        response = FileResponse(
            output_path,
            media_type='audio/mpeg',
            filename='processed_mix.mp3',
            headers={
                "Content-Disposition": "inline; filename=processed_mix.mp3",
                "Accept-Ranges": "bytes"
            }
        )
        
        # Add headers with metadata
        response.headers["X-Vocal-Key"] = str(metadata["vocal_key"])
        response.headers["X-Vocal-BPM"] = str(metadata["vocal_bpm"])
        response.headers["X-Beat-Original-Key"] = str(metadata["beat_key"])
        response.headers["X-Beat-Original-BPM"] = str(metadata["beat_bpm"])
        response.headers["X-Final-Key"] = str(metadata["final_key"])
        response.headers["X-Final-BPM"] = str(metadata["final_bpm"])
        response.headers["X-Offset-Beats"] = str(metadata["offset_beats"])
        
        return response
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error finalizing mix: {str(e)}")
        print(error_details)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "details": error_details}
        )