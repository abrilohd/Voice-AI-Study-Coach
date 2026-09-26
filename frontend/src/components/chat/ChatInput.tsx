import { useState, useRef } from 'react';
import { Send, Mic } from 'lucide-react';
import { useStore } from '../../store';
import { streamRAGChat } from '../../lib/api';
import type { Message } from '../../types';

export default function ChatInput() {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isStreaming || !activeChatId || !activeChat) return;

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
      handleSubmit(e);
    } else if (e.key === 'Escape') {
      setInput('');
    }
  };

  const handleVoiceClick = () => {
    // TODO: Day 6 - Voice functionality
    alert('Voice input coming soon!');
  };

  return (
    <form onSubmit={handleSubmit} style={{ width: '100%' }}>
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
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            padding: 'var(--space-2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--color-text)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--color-text-muted)';
          }}
        >
          <Mic size={18} />
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
    </form>
  );
}
