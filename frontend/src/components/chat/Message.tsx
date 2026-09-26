import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { BookOpen, FileText } from 'lucide-react';
import type { Message as MessageType, Source } from '../../types';
import 'highlight.js/styles/github-dark.css';

interface MessageProps {
  message: MessageType;
}

export default function Message({ message }: MessageProps) {
  if (message.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <div
          style={{
            maxWidth: '70%',
            background: 'var(--color-surface-2)',
            borderRadius: 'var(--radius-lg) var(--radius-sm) var(--radius-lg) var(--radius-lg)',
            padding: '12px 16px',
            fontSize: '15px',
            lineHeight: 1.6,
            color: 'var(--color-text)',
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)' }}>
      {/* Assistant avatar */}
      <div
        style={{
          width: '28px',
          height: '28px',
          borderRadius: '50%',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <BookOpen size={14} style={{ color: 'var(--color-accent)' }} />
      </div>

      {/* Message content */}
      <div style={{ flex: 1, maxWidth: '80%' }}>
        <div style={{ fontSize: '15px', lineHeight: 1.7 }}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              code({ node, inline, className, children, ...props }: any) {
                if (inline) {
                  return (
                    <code
                      style={{
                        background: 'var(--color-surface-2)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '2px 6px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.875em',
                        color: 'var(--color-accent)',
                      }}
                      {...props}
                    >
                      {children}
                    </code>
                  );
                }
                return (
                  <pre
                    style={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                      padding: '16px',
                      overflow: 'auto',
                      marginBlock: '12px',
                    }}
                  >
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                );
              },
              p: ({ children }) => (
                <p style={{ marginBlock: '8px', lineHeight: 1.7 }}>{children}</p>
              ),
              h1: ({ children }) => (
                <h1
                  style={{
                    fontSize: '1.4em',
                    fontWeight: 600,
                    marginTop: '20px',
                    marginBottom: '8px',
                  }}
                >
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2
                  style={{
                    fontSize: '1.2em',
                    fontWeight: 600,
                    marginTop: '16px',
                    marginBottom: '6px',
                  }}
                >
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3
                  style={{
                    fontSize: '1.05em',
                    fontWeight: 600,
                    marginTop: '12px',
                    marginBottom: '4px',
                  }}
                >
                  {children}
                </h3>
              ),
              ul: ({ children }) => (
                <ul
                  style={{
                    paddingLeft: '20px',
                    marginBlock: '8px',
                    lineHeight: 1.7,
                  }}
                >
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol
                  style={{
                    paddingLeft: '20px',
                    marginBlock: '8px',
                    lineHeight: 1.7,
                  }}
                >
                  {children}
                </ol>
              ),
              blockquote: ({ children }) => (
                <blockquote
                  style={{
                    borderLeft: '3px solid var(--color-accent)',
                    paddingLeft: '16px',
                    marginBlock: '12px',
                    color: 'var(--color-text-muted)',
                    fontStyle: 'italic',
                  }}
                >
                  {children}
                </blockquote>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>

          {/* Streaming cursor */}
          {message.isStreaming && (
            <span
              className="cursor"
              style={{
                display: 'inline-block',
                width: '2px',
                height: '1em',
                background: 'var(--color-accent)',
                marginLeft: '2px',
                animation: 'blink 1s step-end infinite',
              }}
            />
          )}
        </div>

        {/* Citation chips */}
        {message.sources && message.sources.length > 0 && (
          <CitationChips sources={message.sources} />
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Citation Chips Component
// ============================================================================

interface CitationChipsProps {
  sources: Source[];
}

function CitationChips({ sources }: CitationChipsProps) {
  return (
    <div
      style={{
        marginTop: '12px',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        alignItems: 'center',
      }}
    >
      <span
        style={{
          fontSize: '11px',
          color: 'var(--color-text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}
      >
        Sources
      </span>
      {sources.map((source, index) => (
        <CitationChip key={`${source.documentId}-${index}`} source={source} />
      ))}
    </div>
  );
}

interface CitationChipProps {
  source: Source;
}

function CitationChip({ source }: CitationChipProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: 'var(--radius-full)',
        border: '1px solid var(--color-accent)',
        background: 'var(--color-accent-dim)',
        fontSize: '12px',
        color: 'var(--color-text)',
        boxShadow: '0 0 8px var(--color-accent-dim)',
        cursor: 'default',
      }}
    >
      <FileText size={11} style={{ color: 'var(--color-accent)' }} />
      {source.documentTitle}
      <span style={{ color: 'var(--color-text-muted)', fontSize: '11px' }}>
        {Math.round(source.similarityScore * 100)}% match
      </span>
    </span>
  );
}
