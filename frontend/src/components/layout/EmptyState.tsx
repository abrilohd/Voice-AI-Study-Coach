import { BookOpen } from 'lucide-react';

interface EmptyStateProps {
  onPromptClick: (prompt: string) => void;
}

const SUGGESTED_PROMPTS = [
  'Explain the main concepts in my uploaded notes',
  'Quiz me on the key terms',
  'Summarize the most important ideas',
  'What topics should I focus on?',
];

export default function EmptyState({ onPromptClick }: EmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100%',
        padding: 'var(--space-8)',
      }}
    >
      <div
        style={{
          textAlign: 'center',
          maxWidth: '600px',
        }}
      >
        {/* Icon */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            marginBottom: 'var(--space-6)',
          }}
        >
          <BookOpen
            size={48}
            style={{
              color: 'var(--color-accent)',
              opacity: 0.6,
            }}
          />
        </div>

        {/* Title */}
        <h2
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '28px',
            fontWeight: 600,
            color: 'var(--color-text)',
            marginBottom: 'var(--space-3)',
            letterSpacing: '-0.02em',
          }}
        >
          Voice AI Study Coach
        </h2>

        {/* Subtitle */}
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: '16px',
            color: 'var(--color-text-muted)',
            marginBottom: 'var(--space-8)',
            lineHeight: 1.5,
          }}
        >
          What would you like to study today?
        </p>

        {/* Suggested prompts */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--space-3)',
            justifyContent: 'center',
          }}
        >
          {SUGGESTED_PROMPTS.map((prompt, index) => (
            <button
              key={index}
              onClick={() => onPromptClick(prompt)}
              style={{
                padding: '6px 14px',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-full)',
                color: 'var(--color-text)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                cursor: 'pointer',
                transition: 'background 0.2s, border-color 0.2s',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-surface-2)';
                e.currentTarget.style.borderColor = 'var(--color-accent)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.borderColor = 'var(--color-border)';
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
