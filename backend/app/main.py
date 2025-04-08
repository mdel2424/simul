import os
import shutil
import tempfile
import torch
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio
from demucs.apply import apply_model

app = FastAPI()

@app.post("/process-audio")
async def process_audio(
    vocal_file: UploadFile = File(...),
    beat_file: UploadFile = File(...)
):
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save uploaded files
        vocal_path = os.path.join(temp_dir, 'vocal.wav')
        beat_path = os.path.join(temp_dir, 'beat.wav')
        
        # Save uploaded files
        with open(vocal_path, 'wb') as f:
            shutil.copyfileobj(vocal_file.file, f)
        
        with open(beat_path, 'wb') as f:
            shutil.copyfileobj(beat_file.file, f)
        
        # Process vocal file with Demucs - extract vocals only
        vocal_output_path = os.path.join(temp_dir, 'vocal_processed')
        os.makedirs(vocal_output_path, exist_ok=True)
        
        try:
            # Load Demucs model
            model = get_model('htdemucs')
            model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
            
            # Process vocal file - keep only vocals
            vocal_audio = AudioFile(vocal_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
            vocal_ref = vocal_audio.mean(0)
            vocal_estimates = apply_model(model, vocal_ref[None], device=model.device)[0]
            
            # Get the vocals stem (usually index 0, but it depends on the model)
            vocal_stem_idx = model.sources.index('vocals')
            vocal_stem = vocal_estimates[vocal_stem_idx]
            
            # Process beat file - remove vocals
            beat_audio = AudioFile(beat_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
            beat_ref = beat_audio.mean(0)
            beat_estimates = apply_model(model, beat_ref[None], device=model.device)[0]
            
            # Get all stems except vocals
            instrumental_sources = [i for i, name in enumerate(model.sources) if name != 'vocals']
            instrumental_stems = [beat_estimates[i] for i in instrumental_sources]
            
            # Combine instrumental stems
            instrumental = sum(instrumental_stems)
            
            # Mix the extracted vocals with instrumental
            final_mix = vocal_stem + instrumental
            
            # Save the final mix
            output_path = os.path.join(temp_dir, 'final_mix.wav')
            save_audio(final_mix, output_path, model.samplerate)
            
            # Return the processed file
            return FileResponse(
                output_path,
                media_type='audio/wav',
                filename='processed_mix.wav'
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")