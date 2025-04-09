import os
import shutil
import tempfile
import torch
import traceback
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio
from demucs.apply import apply_model

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

@app.post("/process-audio")
async def process_audio(
    vocal_file: UploadFile = File(...),
    beat_file: UploadFile = File(...)
):
    # Create a unique output filename
    import uuid
    output_filename = f"processed_mix_{uuid.uuid4()}.mp3"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Print file details for debugging
            print(f"Received vocal file: {vocal_file.filename}, size: {vocal_file.size}")
            print(f"Received beat file: {beat_file.filename}, size: {beat_file.size}")
            
            # Save uploaded files with correct extensions
            vocal_extension = os.path.splitext(vocal_file.filename)[1] or '.mp3'
            beat_extension = os.path.splitext(beat_file.filename)[1] or '.mp3'
            
            vocal_path = os.path.join(temp_dir, f'vocal{vocal_extension}')
            beat_path = os.path.join(temp_dir, f'beat{beat_extension}')
            
            # Save uploaded files
            with open(vocal_path, 'wb') as f:
                content = await vocal_file.read()
                f.write(content)
            await vocal_file.seek(0)  # Reset file pointer
            
            with open(beat_path, 'wb') as f:
                content = await beat_file.read()
                f.write(content)
            await beat_file.seek(0)  # Reset file pointer
            
            print(f"Files saved to: {vocal_path} and {beat_path}")
            
            # Process vocal file with Demucs - extract vocals only
            vocal_output_path = os.path.join(temp_dir, 'vocal_processed')
            os.makedirs(vocal_output_path, exist_ok=True)
            
            # Load Demucs model
            print("Loading Demucs model...")
            model = get_model('htdemucs')
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"Using device: {device}")
            model.to(device)
            
            # Process vocal file - keep only vocals
            print("Processing vocal file...")
            vocal_audio = AudioFile(vocal_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
            if vocal_audio.dim() == 2:
                # If it's 2D (channels, time), add a batch dimension
                vocal_audio = vocal_audio.unsqueeze(0)  # (1, channels, time)
            
            print(f"Vocal audio shape: {vocal_audio.shape}")
            
            vocal_estimates = apply_model(model, vocal_audio, device=device)[0]
            
            # Get the vocals stem (usually index 0, but it depends on the model)
            vocal_stem_idx = model.sources.index('vocals')
            vocal_stem = vocal_estimates[vocal_stem_idx]
            
            # Process beat file - remove vocals
            print("Processing beat file...")
            beat_audio = AudioFile(beat_path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)

            if beat_audio.dim() == 2:
                # If it's 2D (channels, time), add a batch dimension
                beat_audio = beat_audio.unsqueeze(0)  # (1, channels, time)
                
            print(f"Beat audio shape: {beat_audio.shape}")

            beat_estimates = apply_model(model, beat_audio, device=device)[0]
            
            # Get all stems except vocals
            instrumental_sources = [i for i, name in enumerate(model.sources) if name != 'vocals']
            instrumental_stems = [beat_estimates[i] for i in instrumental_sources]
            
            # Combine instrumental stems
            print("Combining stems...")
            instrumental = sum(instrumental_stems)
            
            # Check if the shapes match and adjust if needed
            print(f"Vocal stem shape: {vocal_stem.shape}")
            print(f"Instrumental shape: {instrumental.shape}")
            
            # Make sure they have the same length
            min_length = min(vocal_stem.shape[-1], instrumental.shape[-1])
            vocal_stem = vocal_stem[..., :min_length]
            instrumental = instrumental[..., :min_length]
            
            # Mix the extracted vocals with instrumental
            final_mix = vocal_stem + instrumental
            
            # Save the final mix
            print(f"Saving final mix to {output_path}")
            save_audio(final_mix, output_path, model.samplerate)
            
            # Verify the file exists after saving
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Failed to save audio file to {output_path}")
                
            print(f"File successfully saved to {output_path}")
            
            # Return the processed file
            return FileResponse(
                output_path,
                media_type='audio/mpeg',
                filename='processed_mix.mp3',
                headers={
                    "Content-Disposition": "inline; filename=processed_mix.mp3",
                    "Accept-Ranges": "bytes"
                }
            )
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error processing audio: {str(e)}")
            print(error_details)
            return JSONResponse(
                status_code=500,
                content={"error": str(e), "details": error_details}
            )