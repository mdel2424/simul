import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Container,
  Typography,
  Button,
  Box,
  Input,
  FormControl,
  FormLabel,
  Paper,
  CircularProgress
} from "@mui/material";

const App: React.FC = () => {
  const [vocalAudio, setVocalAudio] = useState<File | null>(null);
  const [beatAudio, setBeatAudio] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processedAudio, setProcessedAudio] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);


  const handleVocalAudioChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setVocalAudio(event.target.files[0]);
    }
  };

  const handleBeatAudioChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setBeatAudio(event.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!vocalAudio || !beatAudio) return;

    setIsProcessing(true);
    setError(null);

    const formData = new FormData();
    formData.append('vocal_file', vocalAudio);
    formData.append('beat_file', beatAudio);

    try {
      const response = await axios.post('/api/process-audio', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: 'blob',
      });

      // Create a download URL for the processed audio
      const url = window.URL.createObjectURL(new Blob([response.data]));
      setProcessedAudio(url);
      setIsProcessing(false);
    } catch (err) {
      console.error('Error processing audio:', err);
      setError('An error occurred while processing the audio files.');
      setIsProcessing(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4, textAlign: 'center' }}>
        <Typography variant="h2" component="h1" gutterBottom>
          simul
        </Typography>

        <Paper elevation={3} sx={{ p: 3, mt: 4 }}>
          <Box sx={{ my: 3 }}>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <FormLabel htmlFor="vocal-audio" sx={{ mb: 1, textAlign: 'left' }}>
                Vocal Audio
              </FormLabel>
              <Input
                id="vocal-audio"
                type="file"
                inputProps={{ accept: "audio/*" }}
                onChange={handleVocalAudioChange}
                fullWidth
              />
              {vocalAudio && (
                <Typography variant="caption" sx={{ mt: 1, textAlign: 'left' }}>
                  Selected: {vocalAudio.name}

                </Typography>
              )}
            </FormControl>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <FormLabel htmlFor="beat-audio" sx={{ mb: 1, textAlign: 'left' }}>
                Beat Audio
              </FormLabel>
              <Input
                id="beat-audio"
                type="file"
                inputProps={{ accept: "audio/*" }}
                onChange={handleBeatAudioChange}
                fullWidth
              />
              {beatAudio && (
                <Typography variant="caption" sx={{ mt: 1, textAlign: 'left' }}>
                  Selected: {beatAudio.name}
                </Typography>
              )}
            </FormControl>

            <Button
              variant="contained"
              color="primary"
              onClick={handleSubmit}
              disabled={!vocalAudio || !beatAudio}
              fullWidth
            >
              Process Audio Files
            </Button>
            {isProcessing && (
              <Box sx={{ mt: 3, textAlign: 'center' }}>
                <Typography>Processing audio files... This may take a few minutes.</Typography>
                {/* You could add a progress indicator here */}
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                  <CircularProgress />
                </Box>
              </Box>
            )}

            {error && (
              <Box sx={{ mt: 3, color: 'error.main' }}>
                <Typography>{error}</Typography>
              </Box>
            )}

            {processedAudio && !isProcessing && (
              <Box sx={{ mt: 3, textAlign: 'center' }}>
                <Button
                  variant="contained"
                  color="success"
                  href={processedAudio}
                  download="processed_audio.mp3"
                  sx={{ mt: 2 }}
                >
                  Download Processed Audio
                </Button>
              </Box>
            )}
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default App;