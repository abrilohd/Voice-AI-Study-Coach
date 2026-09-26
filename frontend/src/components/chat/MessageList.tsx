import { useEffect, useRef } from 'react';
import { useStore } from '../../store';
import Message from './Message';

export default function MessageList() {
  const activeChat = useStore((state) => state.activeChat);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeChat?.messages]);

  return (
    <div
      style={{
        height: '100%',
        overflowY: 'auto',
        padding: '16px 24px 120px',
      }}
    >
      <div
        style={{
          maxWidth: '800px',
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-6)',
        }}
      >
        {activeChat?.messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
