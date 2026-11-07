# Manual Voice Flow Verification Guide

## Prerequisites

- Backend server running (`uv run uvicorn app.main:app --reload --port 8000`)
- Frontend server running (`npm run dev` in frontend directory)
- Valid API keys in `backend/.env`:
  - `ELEVENLABS_API_KEY` for TTS
  - Whisper runs locally (no key needed)
- Test audio file ready (MP3, WAV, WebM, M4A, or OGG format)

## Test Flow 1: Speech-to-Text (STT)

### Step 1: Prepare Test Audio
- Use a short audio recording (< 30 seconds recommended)
- Supported formats: `.mp3`, `.wav`, `.webm`, `.m4a`, `.ogg`
- Keep file size under 25MB
- Sample audio can be recorded using:
  - Windows: Voice Recorder app
  - Browser: Online voice recorder (e.g., voice-recorder-online.com)
  - Command line: `ffmpeg` or `sox`

### Step 2: Test via cURL
```bash
# Login first to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword123"}' \
  > login_response.json

# Extract token (Windows PowerShell)
$TOKEN = (Get-Content login_response.json | ConvertFrom-Json).tokens.access_token

# Transcribe audio file
curl -X POST http://localhost:8000/api/v1/voice/transcribe \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@path/to/your/audio.mp3"
```

### Expected Response:
```json
{
  "text": "Your transcribed text here",
  "duration_hint": "short"  // or "medium" or "long"
}
```

### Validation Checklist:
- [ ] Returns 401 if Authorization header is missing
- [ ] Returns 422 if file format is unsupported (.exe, .txt, etc.)
- [ ] Returns 422 if file exceeds 25MB
- [ ] Returns 200 with transcribed text for valid audio
- [ ] Transcription accuracy is reasonable (>90% for clear English)
- [ ] Response time < 5 seconds for <30s audio clips

---

## Test Flow 2: Text-to-Speech (TTS)

### Step 1: Test via cURL
```bash
# Using token from STT test above

# Synthesize short text
curl -X POST http://localhost:8000/api/v1/voice/synthesize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test of the text to speech system."}' \
  --output test_speech.mp3

# Play the audio (Windows)
start test_speech.mp3

# Or use VLC/other player
vlc test_speech.mp3
```

### Expected Behavior:
- Returns MP3 audio file as binary data
- Audio plays correctly in media player
- Voice quality is clear and natural (ElevenLabs "Rachel" voice)
- No distortion or artifacts

### Validation Checklist:
- [ ] Returns 401 if Authorization header is missing
- [ ] Returns 422 if text exceeds 5000 characters
- [ ] Returns 502 if ElevenLabs API key is invalid/missing
- [ ] Returns 200 with MP3 audio for valid text
- [ ] Audio is clear and understandable
- [ ] Response time < 3 seconds for short texts (<100 chars)
- [ ] Response time < 10 seconds for long texts (<5000 chars)

---

## Test Flow 3: Frontend Voice Integration (Future)

### Once Frontend is Wired:

**Mic Button Flow:**
1. Click microphone button
2. Browser prompts for mic permission (first time only)
3. Speak clearly for 3-10 seconds
4. Click stop button
5. Audio uploads to backend `/transcribe`
6. Transcribed text appears in chat input
7. User reviews and sends message

**TTS Playback Flow:**
1. AI responds to chat message
2. Speaker icon appears next to response
3. Click speaker icon
4. Backend `/synthesize` called with response text
5. Audio plays through browser
6. Progress indicator shows playback status

### Manual Test Scenarios:

#### Scenario 1: Clear English Speech
- **Input**: "Explain the concept of recursion in programming"
- **Expected**: Accurate transcription, AI responds with relevant explanation

#### Scenario 2: Technical Jargon
- **Input**: "What is the difference between async and await in JavaScript"
- **Expected**: Correct transcription of keywords "async" and "await"

#### Scenario 3: Long Response TTS
- **Input**: "Give me a detailed explanation of photosynthesis"
- **Expected**: Long AI response synthesizes correctly, audio is not truncated

#### Scenario 4: Error Handling
- **Input**: Empty audio file (silence for 5 seconds)
- **Expected**: Graceful error message, not a crash

---

## Performance Benchmarks

### STT (Whisper Local)
- **Model**: `base` (74MB RAM)
- **First request**: ~1-2s (model loading)
- **Subsequent requests**: ~0.5-2s (already loaded)
- **5-second audio**: ~0.7s transcription time
- **30-second audio**: ~2s transcription time

### TTS (ElevenLabs)
- **Model**: `eleven_turbo_v2`
- **10 words**: ~0.5-1s
- **100 words**: ~1-2s
- **500 words**: ~3-5s
- **Network latency**: +200-500ms depending on location

### Rate Limits
- **Both endpoints**: 20 requests/minute per user
- **429 status** returned when limit exceeded
- **Retry-After** header indicates wait time in seconds

---

## Troubleshooting

### Issue: "401 Unauthorized"
- **Cause**: Missing or invalid JWT token
- **Fix**: Login first and use the `access_token` in Authorization header

### Issue: "422 Unprocessable Entity - File too large"
- **Cause**: Audio file exceeds 25MB limit
- **Fix**: Compress audio or trim to shorter duration

### Issue: "502 Bad Gateway" on TTS
- **Cause**: ElevenLabs API key missing or invalid
- **Fix**: Check `ELEVENLABS_API_KEY` in backend/.env

### Issue: Transcription returns empty text
- **Cause**: Audio contains only silence or no speech
- **Fix**: Record audio with clear speech

### Issue: Whisper model loading fails
- **Cause**: Insufficient disk space or network issue downloading model
- **Fix**: Check disk space, ensure internet connection for first model download

### Issue: TTS audio is garbled
- **Cause**: Network interruption during download or audio player issue
- **Fix**: Re-request synthesis, try different audio player

---

## Success Criteria

All tests pass when:
- ✅ Authentication is enforced on both endpoints
- ✅ File validation rejects invalid formats and oversized files
- ✅ STT transcribes clear English speech with >90% accuracy
- ✅ TTS produces clear, natural-sounding audio
- ✅ Response times meet performance benchmarks
- ✅ Rate limiting prevents abuse (429 after 20 requests)
- ✅ Error messages are clear and actionable
- ✅ No server crashes or unhandled exceptions

---

## Next Steps

1. **Frontend Integration**: Wire mic button to `/transcribe` endpoint
2. **Audio Recording**: Implement browser MediaRecorder API
3. **TTS Playback**: Add audio player with play/pause/stop controls
4. **Visual Feedback**: Show recording indicator, waveform, progress bars
5. **Error Handling**: Display user-friendly error messages
6. **E2E Test**: Full voice conversation flow (record → transcribe → chat → synthesize → play)

---

## Reference Files

- Backend implementation: `backend/app/api/v1/routers/voice.py`
- Voice service: `backend/app/services/voice_service.py`
- Integration tests: `backend/tests/integration/test_voice.py`
- Unit tests: `backend/tests/unit/test_voice_service.py`
- Voice schemas: `backend/app/schemas/voice.py`
