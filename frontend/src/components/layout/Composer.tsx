import ChatInput from '../chat/ChatInput';

export default function Composer() {
  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 'var(--sidebar-width, 260px)',
        right: 0,
        borderTop: '1px solid var(--color-border)',
        padding: 'var(--space-5) var(--space-6)',
        background: 'var(--color-surface)',
      }}
    >
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <ChatInput />
      </div>
    </div>
  );
}
