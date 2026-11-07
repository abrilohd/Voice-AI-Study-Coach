import { useState, useRef } from 'react';
import { Send, Mic, MicOff, Loader2 } from 'lucide-react';
import { useStore } from '../../store';
import { streamRAGChat } from '../../lib/api';
import type { UseVoiceReturn } from '../../hooks/useVoice';
import type { Message } from '../../types';

interface ChatInputProps {
  onVoiceModeChange?: (isVoiceMode: boolean) => void;
  voiceHook: UseVoiceReturn;
}

export default function ChatInput({ onVoiceModeChange, voiceHook }: ChatInputProps) {
  const [isStreaming, setIsStreaming] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeChat = useStore((state) => state.activeChat);
  const activeChatId = useStore((state) => state.activeChatId);
  const addMessage = useStore((state) => state.addMessage);
  const updateStreamingMessage = useStore((state) => state.updateStreamingMessage);
  const finalizeMessage = useStore((state) => state.finalizeMessage);
  const updateChatTitle = useStore((state) => state.updateChatTitle);
  const input = useStore((state) => state.promptInput);
  const setInput = useStore((state) => state.setPromptInput);

  // Use the passed voice hook
  const voice = voiceHook;

  const handleSubmit = async (e: React.FormEvent, isVoiceInitiated = false) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isStreaming || !activeChatId || !activeChat) return;

    // Notify parent about voice mode
    if (onVoiceModeChange) {
      onVoiceModeChange(isVoiceInitiated);
    }

    // 1. Add user message to store
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      createdAt: new Date(),
    };
    addMessage(activeChatId, userMsg);

    // Auto-title the chat from the first user message
    if (activeChat.messages.length === 0) {
      updateChatTitle(activeChatId, text.slice(0, 40));
    }

    // 2. Add empty assistant message (will stream into it)
    const assistantMsgId = crypto.randomUUID();
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      createdAt: new Date(),
    };
    addMessage(activeChatId, assistantMsg);

    // 3. Clear input, set streaming
    setInput('');
    setIsStreaming(true);

    // 4. Open SSE stream
    const cleanup = streamRAGChat(
      [...activeChat.messages, userMsg],
      activeChat.documentIds.length > 0 ? activeChat.documentIds : undefined,
      (token) => updateStreamingMessage(activeChatId, assistantMsgId, token),
      (done) => {
        const sources = done.sources.map((s) => ({
          documentId: s.document_id || s.document_title,
          documentTitle: s.document_title,
          similarityScore: s.similarity_score,
          chunkIndex: s.chunk_index,
        }));
        finalizeMessage(activeChatId, assistantMsgId, sources);
        setIsStreaming(false);
        cleanupRef.current = null;
      },
      (err) => {
        console.error('Stream error:', err);
        finalizeMessage(activeChatId, assistantMsgId, []);
        setIsStreaming(false);
        cleanupRef.current = null;
      }
    );

    cleanupRef.current = cleanup;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e, false);
    } else if (e.key === 'Escape') {
      setInput('');
    }
  };

  const handleVoiceClick = async () => {
    if (voice.isRecording) {
      await voice.stopRecording();
    } else {
      await voice.startRecording();
    }
  };

  // Determine mic button state
  const getMicIcon = () => {
    if (voice.isTranscribing) {
      return <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />;
    }
    if (voice.isRecording) {
      return <MicOff size={18} />;
    }
    return <Mic size={18} />;
  };

  const getMicColor = () => {
    if (voice.isTranscribing) {
      return 'var(--color-accent)';
    }
    if (voice.isRecording) {
      return '#EF4444';
    }
    return 'var(--color-text-muted)';
  };

  return (
    <>
      <form onSubmit={(e) => handleSubmit(e, false)} style={{ width: '100%' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 'var(--space-3)',
            background: 'var(--color-bg)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-3)',
            transition: 'border-color 0.2s',
          }}
        >
          {/* Voice button */}
          <button
            type="button"
            onClick={handleVoiceClick}
            disabled={isStreaming}
            className={voice.isRecording ? 'recording-pulse' : ''}
            style={{
              position: 'relative',
              background: 'transparent',
              border: 'none',
              color: getMicColor(),
              cursor: isStreaming ? 'not-allowed' : 'pointer',
              padding: 'var(--space-2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.2s',
              opacity: isStreaming ? 0.5 : 1,
            }}
            onMouseEnter={(e) => {
              if (!isStreaming && !voice.isRecording && !voice.isTranscribing) {
                e.currentTarget.style.color = 'var(--color-text)';
              }
            }}
            onMouseLeave={(e) => {
              if (!voice.isRecording && !voice.isTranscribing) {
                e.currentTarget.style.color = 'var(--color-text-muted)';
              }
            }}
          >
            {getMicIcon()}
          </button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your documents..."
            disabled={!activeChat || isStreaming}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--color-text)',
              fontFamily: 'var(--font-body)',
              fontSize: '15px',
              resize: 'none',
              minHeight: '24px',
              maxHeight: '160px',
              lineHeight: 1.5,
            }}
            rows={1}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
            }}
          />

          <button
            type="submit"
            disabled={!input.trim() || !activeChat || isStreaming}
            style={{
              background:
                input.trim() && activeChat && !isStreaming
                  ? 'var(--color-accent)'
                  : 'var(--color-surface-2)',
              border: 'none',
              color:
                input.trim() && activeChat && !isStreaming
                  ? 'var(--color-text)'
                  : 'var(--color-text-muted)',
              cursor:
                input.trim() && activeChat && !isStreaming
                  ? 'pointer'
                  : 'not-allowed',
              padding: 'var(--space-2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 'var(--radius-sm)',
              transition: 'opacity 0.2s',
              minWidth: '28px',
              minHeight: '28px',
            }}
            onMouseEnter={(e) => {
              if (input.trim() && activeChat && !isStreaming) {
                e.currentTarget.style.opacity = '0.8';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '1';
            }}
          >
            <Send size={14} />
          </button>
        </div>

        {/* Voice error display */}
        {voice.error && (
          <div
            style={{
              marginTop: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-3)',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              color: '#EF4444',
            }}
          >
            {voice.error}
          </div>
        )}
      </form>

      {/* CSS for recording pulse animation */}
      <style>{`
        @keyframes pulse-ring {
          0% {
            transform: scale(1);
            opacity: 0.8;
          }
          100% {
            transform: scale(1.6);
            opacity: 0;
          }
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        .recording-pulse::before {
          content: '';
          position: absolute;
          inset: -4px;
          border-radius: 50%;
          border: 2px solid #EF4444;
          animation: pulse-ring 1.2s ease-out infinite;
        }
      `}</style>
    </>
  );
}
