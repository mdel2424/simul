import React, { useState, useRef } from "react";
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

const App = () => {
  const [vocalAudio, setVocalAudio] = useState(null);
  const [beatAudio, setBeatAudio] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedAudio, setProcessedAudio] = useState(null);
  const [error, setError] = useState(null);
  const audioPlayerRef = useRef(null);

  const handleVocalAudioChange = (event) => {
    if (event.target.files && event.target.files[0]) {
      setVocalAudio(event.target.files[0]);
    }
  };

  const handleBeatAudioChange = (event) => {
    if (event.target.files && event.target.files[0]) {
      setBeatAudio(event.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!vocalAudio || !beatAudio) return;

    setIsProcessing(true);
    setError(null);
    setProcessedAudio(null);

    const formData = new FormData();
    formData.append('vocal_file', vocalAudio);
    formData.append('beat_file', beatAudio);

    try {
      console.log("Sending request to process audio...");
      console.log("Vocal file:", vocalAudio.name, "size:", vocalAudio.size);
      console.log("Beat file:", beatAudio.name, "size:", beatAudio.size);
      
      const response = await axios.post('/api/process-audio', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: 'blob',
      });
      
      console.log("Response received:", response);
      
      // Check if we got an error response (could be JSON)
      if (response.headers['content-type'].includes('application/json')) {
        const reader = new FileReader();
        reader.onload = () => {
          const errorData = JSON.parse(reader.result);
          setError(`Server error: ${errorData.error}`);
          console.error('Server error details:', errorData.details);
        };
        reader.readAsText(response.data);
        setIsProcessing(false);
        return;
      }
      
      // Create a download URL for the processed audio
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'audio/mpeg' }));
      setProcessedAudio(url);
      setIsProcessing(false);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.load();
      }

    } catch (err) {
      console.error('Error processing audio:', err);
      // Try to extract more error details if available
      if (err.response && err.response.data) {
        try {
          if (err.response.data instanceof Blob) {
            const reader = new FileReader();
            reader.onload = () => {
              try {
                const errorData = JSON.parse(reader.result);
                setError(`Server error: ${errorData.error || 'Unknown error'}`);
                console.error('Server error details:', errorData.details || 'No details available');
              } catch (parseErr) {
                setError(`Error processing audio: ${err.message}`);
              }
            };
            reader.readAsText(err.response.data);
          } else {
            setError(`Error: ${err.response.data.error || err.message}`);
          }
        } catch (parseErr) {
          setError(`Error processing audio: ${err.message}`);
        }
      } else {
        setError(`Error processing audio: ${err.message}`);
      }
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
              disabled={!vocalAudio || !beatAudio || isProcessing}
              fullWidth
            >
              Process Audio Files
            </Button>
            {isProcessing && (
              <Box sx={{ mt: 3, textAlign: 'center' }}>
                <Typography>Processing audio files... This may take a few minutes.</Typography>
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
                {/* Audio player */}
                <Box sx={{ width: '100%', mb: 2 }}>
                  <audio 
                    ref={audioPlayerRef}
                    controls 
                    style={{ width: '100%' }}
                    src={processedAudio}
                  >
                    Your browser does not support the audio element.
                  </audio>
                </Box>

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