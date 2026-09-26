// ============================================================================
// Message Types
// ============================================================================

export interface Message {
  id: string; // client-generated UUID (crypto.randomUUID())
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[]; // only on assistant messages with RAG
  createdAt: Date;
  isStreaming?: boolean;
}

export interface Source {
  documentId: string;
  documentTitle: string;
  similarityScore: number; // 0.0–1.0
  chunkIndex: number;
}

// ============================================================================
// Document Types
// ============================================================================

export interface DocumentResponse {
  id: string;
  title: string;
  description?: string;
  filename: string;
  fileSizeBytes: number;
  chunkCount: number;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  createdAt: string;
}

export interface DocumentUploadPayload {
  file: File;
  title: string;
  description?: string;
}

// ============================================================================
// Chat Types
// ============================================================================

export interface Chat {
  id: string; // client-generated UUID
  title: string; // first user message, truncated to 40 chars
  messages: Message[];
  documentIds: string[]; // which docs are "pinned" to this chat
  createdAt: Date;
  updatedAt: Date;
}

export interface ChatMessagePayload {
  messages: Message[];
  document_ids?: string[];
  use_rag: boolean;
}

// ============================================================================
// SSE Response Types
// ============================================================================

export interface SSETokenEvent {
  type: 'token';
  content: string;
}

export interface SSEDoneEvent {
  type: 'done';
  data: DonePayload;
}

export interface SSEErrorEvent {
  type: 'error';
  error: string;
}

export type SSEEvent = SSETokenEvent | SSEDoneEvent | SSEErrorEvent;

export interface DonePayload {
  total_tokens: number;
  sources: Array<{
    document_title: string;
    similarity_score: number;
    chunk_index: number;
    document_id: string;
  }>;
}

// ============================================================================
// Auth Types
// ============================================================================

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
}

// ============================================================================
// API Error Types
// ============================================================================

export interface APIError {
  detail: string;
  status?: number;
}

// ============================================================================
// UI State Types
// ============================================================================

export interface UIState {
  sidebarOpen: boolean;
  uploadModalOpen: boolean;
  isLoading: boolean;
}
