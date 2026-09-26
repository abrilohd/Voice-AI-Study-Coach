import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { Chat, Message, Source, DocumentResponse } from '../types';
import { setToken as setApiToken, clearToken as clearApiToken } from '../lib/api';

// ============================================================================
// Store Interface
// ============================================================================

interface AppStore {
  // Auth
  token: string | null;
  setToken: (token: string) => void;
  logout: () => void;

  // Chats
  chats: Chat[];
  activeChatId: string | null;
  activeChat: Chat | undefined;
  createChat: () => void;
  setActiveChat: (id: string) => void;
  addMessage: (chatId: string, message: Message) => void;
  updateStreamingMessage: (chatId: string, messageId: string, delta: string) => void;
  finalizeMessage: (chatId: string, messageId: string, sources: Source[]) => void;
  updateChatTitle: (chatId: string, title: string) => void;
  deleteChat: (id: string) => void;
  toggleDocumentInChat: (chatId: string, documentId: string) => void;

  // Documents
  documents: DocumentResponse[];
  setDocuments: (docs: DocumentResponse[]) => void;
  addDocument: (doc: DocumentResponse) => void;
  removeDocument: (id: string) => void;
  updateDocument: (id: string, updates: Partial<DocumentResponse>) => void;

  // UI state
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  promptInput: string;
  setPromptInput: (input: string) => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

function generateChatTitle(firstMessage: string): string {
  const maxLength = 40;
  if (firstMessage.length <= maxLength) {
    return firstMessage;
  }
  return firstMessage.slice(0, maxLength).trim() + '...';
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // ========================================================================
      // Auth
      // ========================================================================
      token: null,

      setToken: (token: string) => {
        setApiToken(token);
        set({ token });
      },

      logout: () => {
        clearApiToken();
        set({
          token: null,
          chats: [],
          activeChatId: null,
          documents: [],
        });
      },

      // ========================================================================
      // Chats
      // ========================================================================
      chats: [],
      activeChatId: null,

      get activeChat() {
        const state = get();
        return state.chats.find((chat) => chat.id === state.activeChatId);
      },

      createChat: () => {
        const newChat: Chat = {
          id: crypto.randomUUID(),
          title: 'New Chat',
          messages: [],
          documentIds: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };

        set((state) => ({
          chats: [newChat, ...state.chats],
          activeChatId: newChat.id,
        }));
      },

      setActiveChat: (id: string) => {
        set({ activeChatId: id });
      },

      addMessage: (chatId: string, message: Message) => {
        set((state) => {
          const chats = state.chats.map((chat) => {
            if (chat.id !== chatId) return chat;

            const updatedMessages = [...chat.messages, message];
            let updatedTitle = chat.title;

            // Update title if this is the first user message
            if (
              message.role === 'user' &&
              chat.messages.length === 0 &&
              chat.title === 'New Chat'
            ) {
              updatedTitle = generateChatTitle(message.content);
            }

            return {
              ...chat,
              messages: updatedMessages,
              title: updatedTitle,
              updatedAt: new Date(),
            };
          });

          return { chats };
        });
      },

      updateStreamingMessage: (chatId: string, messageId: string, delta: string) => {
        set((state) => {
          const chats = state.chats.map((chat) => {
            if (chat.id !== chatId) return chat;

            const messages = chat.messages.map((msg) => {
              if (msg.id !== messageId) return msg;
              return {
                ...msg,
                content: msg.content + delta,
                isStreaming: true,
              };
            });

            return {
              ...chat,
              messages,
              updatedAt: new Date(),
            };
          });

          return { chats };
        });
      },

      finalizeMessage: (chatId: string, messageId: string, sources: Source[]) => {
        set((state) => {
          const chats = state.chats.map((chat) => {
            if (chat.id !== chatId) return chat;

            const messages = chat.messages.map((msg) => {
              if (msg.id !== messageId) return msg;
              return {
                ...msg,
                isStreaming: false,
                sources: sources.length > 0 ? sources : undefined,
              };
            });

            return {
              ...chat,
              messages,
              updatedAt: new Date(),
            };
          });

          return { chats };
        });
      },

      updateChatTitle: (chatId: string, title: string) => {
        set((state) => {
          const chats = state.chats.map((chat) => {
            if (chat.id !== chatId) return chat;
            return { ...chat, title, updatedAt: new Date() };
          });
          return { chats };
        });
      },

      deleteChat: (id: string) => {
        set((state) => {
          const chats = state.chats.filter((chat) => chat.id !== id);
          const activeChatId =
            state.activeChatId === id
              ? chats.length > 0
                ? chats[0].id
                : null
              : state.activeChatId;

          return { chats, activeChatId };
        });
      },

      toggleDocumentInChat: (chatId: string, documentId: string) => {
        set((state) => {
          const chats = state.chats.map((chat) => {
            if (chat.id !== chatId) return chat;

            const documentIds = chat.documentIds.includes(documentId)
              ? chat.documentIds.filter((id) => id !== documentId)
              : [...chat.documentIds, documentId];

            return {
              ...chat,
              documentIds,
              updatedAt: new Date(),
            };
          });

          return { chats };
        });
      },

      // ========================================================================
      // Documents
      // ========================================================================
      documents: [],

      setDocuments: (docs: DocumentResponse[]) => {
        set({ documents: docs });
      },

      addDocument: (doc: DocumentResponse) => {
        set((state) => ({
          documents: [doc, ...state.documents],
        }));
      },

      removeDocument: (id: string) => {
        set((state) => ({
          documents: state.documents.filter((doc) => doc.id !== id),
          // Remove document from all chats
          chats: state.chats.map((chat) => ({
            ...chat,
            documentIds: chat.documentIds.filter((docId) => docId !== id),
          })),
        }));
      },

      updateDocument: (id: string, updates: Partial<DocumentResponse>) => {
        set((state) => ({
          documents: state.documents.map((doc) =>
            doc.id === id ? { ...doc, ...updates } : doc
          ),
        }));
      },

      // ========================================================================
      // UI State
      // ========================================================================
      sidebarOpen: true,

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      promptInput: '',

      setPromptInput: (input: string) => {
        set({ promptInput: input });
      },
    }),
    {
      name: 'voice-ai-study-coach',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        token: state.token,
        chats: state.chats,
        documents: state.documents,
        sidebarOpen: state.sidebarOpen,
        activeChatId: state.activeChatId,
      }),
    }
  )
);
