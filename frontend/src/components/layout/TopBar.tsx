import { Menu } from 'lucide-react';
import { useStore } from '../../store';

export default function TopBar() {
  const activeChat = useStore((state) => state.activeChat);
  const toggleSidebar = useStore((state) => state.toggleSidebar);

  return (
    <div
      style={{
        height: '56px',
        borderBottom: '1px solid var(--color-border)',
        padding: '0 var(--space-6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'var(--color-bg)',
      }}
    >
      {/* Left side: mobile menu + chat title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
        <button
          className="md:hidden"
          onClick={toggleSidebar}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--color-text)',
            cursor: 'pointer',
            padding: 'var(--space-2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Menu size={20} />
        </button>

        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '15px',
            fontWeight: 500,
            color: 'var(--color-text)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {activeChat?.title || 'Voice AI Study Coach'}
        </h1>
      </div>

      {/* Right side: model badge */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <span
          style={{
            padding: 'var(--space-2) var(--space-3)',
            background: 'var(--color-surface-2)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            fontFamily: 'var(--font-mono)',
            fontWeight: 400,
          }}
        >
          claude-sonnet-4-6
        </span>
      </div>
    </div>
  );
}
