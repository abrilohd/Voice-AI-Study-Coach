import { useState, useRef, useCallback } from 'react';
import { getToken } from '../lib/api';

export interface UseVoiceReturn {
  isRecording: boolean;
  isTranscribing: boolean;
  isSpeaking: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  speak: (text: string) => Promise<void>;
  stopSpeaking: () => void;
  error: string | null;
}

const BASE_URL = import.meta.env.VITE_API_URL || '';

export function useVoice(onTranscription: (text: string) => void): UseVoiceReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Create MediaRecorder with webm codec
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
        
        // Release microphone
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        // Send to transcription
        await sendToTranscription(audioBlob);
      };

      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording:', err);
      
      if (err instanceof Error && err.name === 'NotAllowedError') {
        setError('Microphone access required. Click the lock icon in your browser address bar.');
      } else {
        setError('Failed to access microphone. Please check your browser permissions.');
      }
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, []);

  const sendToTranscription = useCallback(
    async (audioBlob: Blob) => {
      setIsTranscribing(true);
      setError(null);

      try {
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        const token = getToken();
        const headers: Record<string, string> = {};
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${BASE_URL}/api/v1/voice/transcribe`, {
          method: 'POST',
          headers,
          body: formData,
        });

        if (!response.ok) {
          throw new Error('Transcription failed. please try again');
        }

        const data = await response.json();
        
        if (!data.text || data.text.trim().length === 0) {
          setError('No speech detected — try again');
          setIsTranscribing(false);
          return;
        }

        // Fire callback to fill composer input
        onTranscription(data.text);
        setIsTranscribing(false);
      } catch (err) {
        console.error('Transcription error:', err);
        setError(err instanceof Error ? err.message : 'Transcription failed. please try again');
        setIsTranscribing(false);
      }
    },
    [onTranscription]
  );

  const speak = useCallback(async (text: string) => {
    if (!text || text.length > 5000) {
      return;
    }

    setIsSpeaking(true);
    setError(null);

    try {
      const token = getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${BASE_URL}/api/v1/voice/synthesize`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        // TTS failure is non-fatal — user already saw the text
        console.error('TTS failed:', response.statusText);
        setIsSpeaking(false);
        return;
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl); // Clean up memory
        audioRef.current = null;
      };

      audio.onerror = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
      };

      await audio.play();
    } catch (err) {
      console.error('TTS error:', err);
      setIsSpeaking(false);
    }
  }, []);

  const stopSpeaking = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsSpeaking(false);
  }, []);

  return {
    isRecording,
    isTranscribing,
    isSpeaking,
    startRecording,
    stopRecording,
    speak,
    stopSpeaking,
    error,
  };
}
