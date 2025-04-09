import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import {
  Container, Typography, Button, Box, Input, TextField,
  FormControl, FormLabel, Paper, CircularProgress, Grid,
  MenuItem, Select, InputLabel, CssBaseline, IconButton,
  Slider, Stack, Badge, Tooltip
} from "@mui/material";
import { ThemeProvider, createTheme } from '@mui/material/styles'; 
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import MergeIcon from '@mui/icons-material/Merge';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const theme = createTheme({
  palette: {
    mode: 'dark',
  },
});

const App = () => {
  const [vocalAudio, setVocalAudio] = useState(null);
  const [beatAudio, setBeatAudio] = useState(null);
  const [vocalKey, setVocalKey] = useState("");
  const [beatKey, setBeatKey] = useState("");
  const [vocalBpm, setVocalBpm] = useState("");
  const [beatBpm, setBeatBpm] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedAudio, setProcessedAudio] = useState(null);
  const [error, setError] = useState(null);
  const audioPlayerRef = useRef(null);
  
  // New state variables for vocal offset adjustment workflow
  const [processingId, setProcessingId] = useState(null);
  const [offsetBeats, setOffsetBeats] = useState(0);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isAdjusting, setIsAdjusting] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [isPreviewMode, setIsPreviewMode] = useState(false);

  // Musical keys available
  const musicalKeys = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
    "Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "A#m", "Bm"
  ];

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
    setIsPreviewMode(false);

    const formData = new FormData();
    formData.append('vocal_file', vocalAudio);
    formData.append('beat_file', beatAudio);

    // Add the key and BPM information to the form data
    if (vocalKey) formData.append('vocal_key', vocalKey);
    if (beatKey) formData.append('beat_key', beatKey);
    if (vocalBpm) formData.append('vocal_bpm', vocalBpm);
    if (beatBpm) formData.append('beat_bpm', beatBpm);

    try {
      console.log("Sending request to prepare audio...");
      
      const response = await axios.post('/api/prepare-audio', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      
      console.log("Response received:", response.data);
      
      // Set the preview mode and necessary data for adjustment
      setProcessingId(response.data.processing_id);
      setPreviewUrl(`/api${response.data.preview_url}`);
      setOffsetBeats(response.data.offset_beats || 0);
      setIsPreviewMode(true);
      setIsProcessing(false);

    } catch (err) {
      console.error('Error processing audio:', err);
      handleApiError(err);
      setIsProcessing(false);
    }
  };

  const handleApiError = (err) => {
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
  };

  const handleOffsetChange = async (newOffset) => {
    if (!processingId) return;

    setIsAdjusting(true);
    setOffsetBeats(newOffset);

    try {
      const formData = new FormData();
      formData.append('processing_id', processingId);
      formData.append('offset_beats', newOffset);

      const response = await axios.post('/api/adjust-offset', formData);
      console.log("Offset adjustment response:", response.data);

      // Update the preview URL with a timestamp to force reload
      setPreviewUrl(`/api${response.data.preview_url}?t=${Date.now()}`);
      
      setIsAdjusting(false);
    } catch (err) {
      console.error('Error adjusting offset:', err);
      handleApiError(err);
      setIsAdjusting(false);
    }
  };

  const handleQuarterBeatAdjustment = (direction) => {
    // Adjust by 0.25 beats (one quarter beat) in the specified direction
    const newOffset = offsetBeats + (direction * 0.25);
    handleOffsetChange(newOffset);
  };

  const resetOffset = () => {
    handleOffsetChange(0);
  };

  const handleFinalizeMix = async () => {
    if (!processingId) return;

    setIsMerging(true);

    try {
      const formData = new FormData();
      formData.append('processing_id', processingId);

      const response = await axios.post('/api/finalize-mix', formData, {
        responseType: 'blob',
      });

      // Create a download URL for the processed audio
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'audio/mpeg' }));
      setProcessedAudio(url);
      setIsPreviewMode(false);
      
      if (audioPlayerRef.current) {
        audioPlayerRef.current.load();
      }
      
      setIsMerging(false);
    } catch (err) {
      console.error('Error finalizing mix:', err);
      handleApiError(err);
      setIsMerging(false);
    }
  };

  // Clean up URLs when component unmounts
  useEffect(() => {
    return () => {
      if (processedAudio) {
        URL.revokeObjectURL(processedAudio);
      }
    };
  }, [processedAudio]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="md">
        <Box sx={{ my: 4, textAlign: 'center' }}>
          <Typography variant="h2" component="h1" gutterBottom>
            simul
          </Typography>

          <Paper elevation={3} sx={{ p: 3, mt: 4 }}>
            <Box sx={{ my: 3 }}>
              {!isPreviewMode && !processedAudio && (
                <>
                  {/* Vocal Audio Section */}
                  <Typography variant="h6" gutterBottom sx={{ textAlign: 'left', mb: 2 }}>
                    Vocal Track
                  </Typography>
                  
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <FormLabel htmlFor="vocal-audio" sx={{ mb: 1, textAlign: 'left' }}>
                      Audio File
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

                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={6}>
                      <FormControl fullWidth>
                        <InputLabel id="vocal-key-label">Key</InputLabel>
                        <Select
                          labelId="vocal-key-label"
                          id="vocal-key"
                          value={vocalKey}
                          label="Key"
                          onChange={(e) => setVocalKey(e.target.value)}
                        >
                          <MenuItem value=""><em>Unknown</em></MenuItem>
                          {musicalKeys.map((key) => (
                            <MenuItem key={key} value={key}>{key}</MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="BPM"
                        type="number"
                        fullWidth
                        value={vocalBpm}
                        onChange={(e) => setVocalBpm(e.target.value)}
                        inputProps={{ min: 40, max: 300 }}
                      />
                    </Grid>
                  </Grid>

                  {/* Beat Audio Section */}
                  <Typography variant="h6" gutterBottom sx={{ textAlign: 'left', mb: 2, mt: 4 }}>
                    Beat Track
                  </Typography>
                  
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <FormLabel htmlFor="beat-audio" sx={{ mb: 1, textAlign: 'left' }}>
                      Audio File
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

                  <Grid container spacing={2} sx={{ mb: 4 }}>
                    <Grid item xs={6}>
                      <FormControl fullWidth>
                        <InputLabel id="beat-key-label">Key</InputLabel>
                        <Select
                          labelId="beat-key-label"
                          id="beat-key"
                          value={beatKey}
                          label="Key"
                          onChange={(e) => setBeatKey(e.target.value)}
                        >
                          <MenuItem value=""><em>Unknown</em></MenuItem>
                          {musicalKeys.map((key) => (
                            <MenuItem key={key} value={key}>{key}</MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="BPM"
                        type="number"
                        fullWidth
                        value={beatBpm}
                        onChange={(e) => setBeatBpm(e.target.value)}
                        inputProps={{ min: 40, max: 300 }}
                      />
                    </Grid>
                  </Grid>

                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleSubmit}
                    disabled={!vocalAudio || !beatAudio || isProcessing}
                    fullWidth
                    sx={{ mt: 2 }}
                    size="large"
                  >
                    Process Audio Files
                  </Button>
                </>
              )}
              
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

              {isPreviewMode && previewUrl && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom sx={{ textAlign: 'center' }}>
                    Adjust Vocal Timing
                  </Typography>
                  
                  {/* Preview audio player */}
                  <Box sx={{ width: '100%', mb: 3 }}>
                    <audio 
                      ref={audioPlayerRef}
                      controls 
                      autoPlay={false}
                      style={{ width: '100%' }}
                      src={previewUrl}
                    >
                      Your browser does not support the audio element.
                    </audio>
                  </Box>
                  
                  {/* Offset controls */}
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Vocal Offset: {offsetBeats.toFixed(2)} beats
                    </Typography>
                    
                    <Stack 
                      direction="row" 
                      spacing={2} 
                      alignItems="center" 
                      justifyContent="center"
                      sx={{ mb: 2 }}
                    >
                      <Tooltip title="Move vocals earlier (backward)">
                        <IconButton 
                          color="primary" 
                          onClick={() => handleQuarterBeatAdjustment(-1)}
                          disabled={isAdjusting}
                        >
                          <ArrowBackIcon />
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Reset offset to 0">
                        <IconButton 
                          color="secondary" 
                          onClick={resetOffset}
                          disabled={isAdjusting || offsetBeats === 0}
                        >
                          <RestartAltIcon />
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Move vocals later (forward)">
                        <IconButton 
                          color="primary" 
                          onClick={() => handleQuarterBeatAdjustment(1)}
                          disabled={isAdjusting}
                        >
                          <ArrowForwardIcon />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                    
                    {isAdjusting && (
                      <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
                        <CircularProgress size={24} />
                      </Box>
                    )}
                    
                    <Typography variant="caption" sx={{ display: 'block', textAlign: 'center', mb: 3 }}>
                      Use the buttons to adjust vocal timing by quarter beats.
                    </Typography>
                    
                    <Button
                      variant="contained"
                      color="success"
                      fullWidth
                      startIcon={<MergeIcon />}
                      onClick={handleFinalizeMix}
                      disabled={isMerging}
                      sx={{ mt: 2 }}
                    >
                      Finalize Mix
                    </Button>
                    
                    {isMerging && (
                      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                        <CircularProgress size={24} />
                      </Box>
                    )}
                  </Box>
                </Box>
              )}
              
              {processedAudio && !isProcessing && !isPreviewMode && (
                <Box sx={{ mt: 3, textAlign: 'center' }}>
                  <Typography variant="h6" gutterBottom>
                    Final Mix <CheckCircleIcon color="success" sx={{ verticalAlign: 'middle', ml: 1 }} />
                  </Typography>
                  
                  {/* Audio player */}
                  <Box sx={{ width: '100%', mb: 2 }}>
                    <audio 
                      ref={audioPlayerRef}
                      controls 
                      autoPlay={false}
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
                  
                  <Button
                    variant="outlined"
                    color="primary"
                    onClick={() => {
                      setIsPreviewMode(false);
                      setProcessedAudio(null);
                      setProcessingId(null);
                      setPreviewUrl(null);
                      setOffsetBeats(0);
                    }}
                    sx={{ mt: 2, ml: 2 }}
                  >
                    New Mix
                  </Button>
                </Box>
              )}
            </Box>
          </Paper>
        </Box>
      </Container>
    </ThemeProvider>
  );
};

export default App;