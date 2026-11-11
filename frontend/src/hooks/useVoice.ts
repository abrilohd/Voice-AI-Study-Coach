import { useState, useRef, useCallback } from 'react';
import { transcribeAudio } from '../lib/api';

type VoiceState = 'idle' | 'recording' | 'transcribing';

export interface UseVoiceReturn {
  state: VoiceState;
  error: string | null;
  start: () => Promise<void>;
  stop: () => Promise<void>;
}

export function useVoice(onTranscription: (text: string) => void): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>('idle');
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const start = useCallback(async () => {
    try {
      setError(null);
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Create MediaRecorder with webm codec (best browser support)
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Collect audio chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Handle recording stop
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Release microphone tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        // Transcribe the audio
        setState('transcribing');
        try {
          const text = await transcribeAudio(audioBlob);
          
          if (!text || text.trim().length === 0) {
            setError('No speech detected. Please try again.');
            setState('idle');
            return;
          }

          // Fill composer input with transcribed text
          onTranscription(text);
          setState('idle');
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'Transcription failed';
          setError(errorMessage);
          setState('idle');
        }
      };

      // Start recording
      mediaRecorder.start();
      setState('recording');
    } catch (err) {
      console.error('Failed to start recording:', err);
      
      if (err instanceof Error && err.name === 'NotAllowedError') {
        setError('Microphone permission denied. Check browser settings.');
      } else {
        setError('Failed to access microphone');
      }
      setState('idle');
    }
  }, [onTranscription]);

  const stop = useCallback(async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      // setState will be updated in the onstop handler
    }
  }, []);

  return {
    state,
    error,
    start,
    stop,
  };
}
