import { Menu, Volume2, VolumeX } from 'lucide-react';
import { useStore } from '../../store';

interface TopBarProps {
  isSpeaking?: boolean;
  onStopSpeaking?: () => void;
}

export default function TopBar({ isSpeaking = false, onStopSpeaking }: TopBarProps) {
  const activeChat = useStore((state) => state.activeChat);
  const toggleSidebar = useStore((state) => state.toggleSidebar);
  const voiceEnabled = useStore((state) => state.voiceEnabled);
  const setVoiceEnabled = useStore((state) => state.setVoiceEnabled);

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

      {/* Right side: speaking indicator + voice toggle + model badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        {/* Speaking indicator */}
        {isSpeaking && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-3)',
              background: 'var(--color-surface-2)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <Volume2
              size={14}
              style={{
                color: 'var(--color-accent)',
                animation: 'pulse-opacity 1.5s ease-in-out infinite',
              }}
            />
            <span
              style={{
                fontSize: '11px',
                color: 'var(--color-text-muted)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              Speaking...
            </span>
            {onStopSpeaking && (
              <button
                onClick={onStopSpeaking}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center',
                  color: 'var(--color-text-muted)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--color-text)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--color-text-muted)';
                }}
              >
                <VolumeX size={12} />
              </button>
            )}
          </div>
        )}

        {/* Voice toggle */}
        <button
          onClick={() => setVoiceEnabled(!voiceEnabled)}
          title={voiceEnabled ? 'Disable voice responses' : 'Enable voice responses'}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: 'var(--space-2)',
            display: 'flex',
            alignItems: 'center',
            color: voiceEnabled ? 'var(--color-accent)' : 'var(--color-text-muted)',
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => {
            if (!voiceEnabled) {
              e.currentTarget.style.color = 'var(--color-text)';
            }
          }}
          onMouseLeave={(e) => {
            if (!voiceEnabled) {
              e.currentTarget.style.color = 'var(--color-text-muted)';
            }
          }}
        >
          {voiceEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>

        {/* Model badge */}
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

      {/* CSS for pulse animation */}
      <style>{`
        @keyframes pulse-opacity {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
