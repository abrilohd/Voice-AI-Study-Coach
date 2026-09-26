import { BookOpen, Plus, Paperclip, X, LogOut } from 'lucide-react';
import { useState } from 'react';
import { useStore } from '../../store';
import type { DocumentResponse } from '../../types';
import UploadModal from '../documents/UploadModal';

export default function Sidebar() {
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  
  const sidebarOpen = useStore((state) => state.sidebarOpen);
  const toggleSidebar = useStore((state) => state.toggleSidebar);
  const chats = useStore((state) => state.chats);
  const activeChatId = useStore((state) => state.activeChatId);
  const documents = useStore((state) => state.documents);
  const createChat = useStore((state) => state.createChat);
  const setActiveChat = useStore((state) => state.setActiveChat);
  const logout = useStore((state) => state.logout);

  const handleNewChat = () => {
    createChat();
  };

  const handleChatClick = (chatId: string) => {
    setActiveChat(chatId);
  };

  const formatRelativeTime = (date: Date): string => {
    const now = new Date();
    const diff = now.getTime() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(date).toLocaleDateString();
  };

  const truncate = (text: string, maxLength: number): string => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + '...';
  };

  const getStatusIndicator = (status: DocumentResponse['status']) => {
    switch (status) {
      case 'ready':
        return (
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--color-success)',
              display: 'inline-block',
            }}
          />
        );
      case 'processing':
        return (
          <span
            className="animate-pulse"
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--color-warning)',
              display: 'inline-block',
            }}
          />
        );
      case 'failed':
        return (
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--color-error)',
              display: 'inline-block',
            }}
          />
        );
      default:
        return null;
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="md:hidden"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 40,
          }}
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          width: '260px',
          background: 'var(--color-surface)',
          borderRight: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 50,
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.2s ease',
        }}
        className="md:translate-x-0"
      >
        {/* Logo area */}
        <div
          style={{
            padding: 'var(--space-5)',
            position: 'relative',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <BookOpen size={20} style={{ color: 'var(--color-accent)' }} />
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '15px',
                color: 'var(--color-text)',
              }}
            >
              Study Coach
            </span>
          </div>

          {/* Mobile close button */}
          <button
            className="md:hidden"
            onClick={toggleSidebar}
            style={{
              position: 'absolute',
              top: 'var(--space-5)',
              right: 'var(--space-5)',
              background: 'transparent',
              border: 'none',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              padding: 'var(--space-1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Horizontal rule */}
        <div
          style={{
            height: '1px',
            background: 'var(--color-border)',
            marginBottom: 'var(--space-1)',
          }}
        />

        {/* New chat button */}
        <div style={{ padding: 'var(--space-4)' }}>
          <button
            onClick={handleNewChat}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-3)',
              background: 'transparent',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text)',
              fontFamily: 'var(--font-body)',
              fontSize: '14px',
              fontWeight: 400,
              cursor: 'pointer',
              transition: 'background 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--color-surface-2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
          >
            <Plus size={18} />
            <span>New chat</span>
          </button>
        </div>

        {/* Chat history list */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '0 var(--space-4) var(--space-4)',
          }}
        >
          {chats.length === 0 ? (
            <div
              style={{
                padding: 'var(--space-6) var(--space-4)',
                textAlign: 'center',
                color: 'var(--color-text-muted)',
                fontSize: '13px',
                lineHeight: 1.5,
              }}
            >
              Your chat history will appear here
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              {chats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => handleChatClick(chat.id)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    gap: 'var(--space-1)',
                    padding: 'var(--space-3)',
                    background:
                      activeChatId === chat.id ? 'var(--color-surface-2)' : 'transparent',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-text)',
                    fontFamily: 'var(--font-body)',
                    fontSize: '14px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.2s',
                    position: 'relative',
                  }}
                  onMouseEnter={(e) => {
                    if (activeChatId !== chat.id) {
                      e.currentTarget.style.background = 'var(--color-surface-2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeChatId !== chat.id) {
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  {activeChatId === chat.id && (
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: 0,
                        bottom: 0,
                        width: '2px',
                        background: 'var(--color-accent)',
                      }}
                    />
                  )}
                  <span
                    style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      width: '100%',
                      fontWeight: activeChatId === chat.id ? 500 : 400,
                    }}
                  >
                    {truncate(chat.title, 36)}
                  </span>
                  <span
                    style={{
                      fontSize: '11px',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    {formatRelativeTime(chat.updatedAt)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Documents section */}
        <div
          style={{
            borderTop: '1px solid var(--color-border)',
            padding: 'var(--space-5) var(--space-4)',
            background: 'var(--color-bg)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 'var(--space-4)',
            }}
          >
            <span
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--color-text-muted)',
                fontWeight: 500,
              }}
            >
              Documents
            </span>
            <button
              onClick={() => setUploadModalOpen(true)}
              style={{
                background: 'var(--color-surface-2)',
                border: 'none',
                color: 'var(--color-text)',
                cursor: 'pointer',
                padding: 'var(--space-2) var(--space-3)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                fontSize: '12px',
                fontFamily: 'var(--font-body)',
                fontWeight: 500,
                borderRadius: 'var(--radius-sm)',
                transition: 'background 0.3s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-surface)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--color-surface-2)';
              }}
            >
              <Paperclip size={14} />
              <span>Upload</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {documents.length === 0 ? (
              <div
                style={{
                  padding: 'var(--space-4) var(--space-3)',
                  textAlign: 'center',
                  color: 'var(--color-text-muted)',
                  fontSize: '12px',
                  lineHeight: 1.5,
                }}
              >
                Upload PDFs to get started
              </div>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-3)',
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '13px',
                    color: 'var(--color-text)',
                  }}
                >
                  {getStatusIndicator(doc.status)}
                  <span
                    style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1,
                    }}
                  >
                    {truncate(doc.filename, 24)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Logout button */}
        <div
          style={{
            borderTop: '1px solid var(--color-border)',
            padding: 'var(--space-4)',
          }}
        >
          <button
            onClick={logout}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-3)',
              background: 'transparent',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-muted)',
              fontFamily: 'var(--font-body)',
              fontSize: '13px',
              fontWeight: 400,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--color-surface-2)';
              e.currentTarget.style.color = 'var(--color-text)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--color-text-muted)';
            }}
          >
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Upload modal */}
      <UploadModal isOpen={uploadModalOpen} onClose={() => setUploadModalOpen(false)} />
    </>
  );
}
