import { useState, FormEvent } from 'react';
import { BookOpen } from 'lucide-react';
import { useStore } from '../../store';
import { login, register } from '../../lib/api';

type Tab = 'signin' | 'signup';

export default function AuthScreen() {
  const [tab, setTab] = useState<Tab>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const setToken = useStore((s) => s.setToken);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = tab === 'signin' 
        ? await login(email, password)
        : await register(email, password);

      setToken(response.access_token);
      // App will re-render to workspace
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'var(--color-bg)',
        padding: '24px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '400px',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: '32px',
        }}
      >
        {/* Icon & Title */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <BookOpen
            size={36}
            style={{
              color: 'var(--color-accent)',
              marginBottom: '16px',
              display: 'inline-block',
            }}
          />
          <h1
            style={{
              fontSize: '1.5rem',
              fontWeight: 600,
              color: 'var(--color-text)',
              margin: 0,
            }}
          >
            Voice AI Study Coach
          </h1>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: 'flex',
            gap: '24px',
            marginBottom: '24px',
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <button
            type="button"
            onClick={() => {
              setTab('signin');
              setError('');
            }}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '8px 0',
              fontSize: '0.9375rem',
              fontWeight: 500,
              color: tab === 'signin' ? 'var(--color-text)' : 'var(--color-text-muted)',
              borderBottom: tab === 'signin' ? '2px solid var(--color-accent)' : '2px solid transparent',
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontFamily: 'var(--font-body)',
            }}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => {
              setTab('signup');
              setError('');
            }}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '8px 0',
              fontSize: '0.9375rem',
              fontWeight: 500,
              color: tab === 'signup' ? 'var(--color-text)' : 'var(--color-text-muted)',
              borderBottom: tab === 'signup' ? '2px solid var(--color-accent)' : '2px solid transparent',
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontFamily: 'var(--font-body)',
            }}
          >
            Sign up
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label
              htmlFor="email"
              style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                color: 'var(--color-text)',
                marginBottom: '6px',
              }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text)',
                fontSize: '0.9375rem',
                fontFamily: 'var(--font-body)',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => (e.target.style.borderColor = 'var(--color-accent)')}
              onBlur={(e) => (e.target.style.borderColor = 'var(--color-border)')}
            />
          </div>

          <div>
            <label
              htmlFor="password"
              style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                color: 'var(--color-text)',
                marginBottom: '6px',
              }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete={tab === 'signin' ? 'current-password' : 'new-password'}
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text)',
                fontSize: '0.9375rem',
                fontFamily: 'var(--font-body)',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => (e.target.style.borderColor = 'var(--color-accent)')}
              onBlur={(e) => (e.target.style.borderColor = 'var(--color-border)')}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '12px',
              marginTop: '8px',
              background: 'var(--color-accent)',
              color: 'var(--color-text)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.9375rem',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.6 : 1,
              transition: 'all 0.2s',
              fontFamily: 'var(--font-body)',
            }}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.background = 'var(--color-accent-dim)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--color-accent)';
            }}
          >
            {isLoading ? 'Loading...' : tab === 'signin' ? 'Sign in' : 'Create account'}
          </button>

          {/* Error message */}
          {error && (
            <div
              style={{
                padding: '10px 12px',
                background: 'rgba(248, 113, 113, 0.1)',
                border: '1px solid var(--color-error)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-error)',
                fontSize: '0.875rem',
                lineHeight: 1.4,
              }}
            >
              {error}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
