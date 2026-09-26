import type {
  AuthResponse,
  LoginPayload,
  RegisterPayload,
  DocumentResponse,
  DocumentUploadPayload,
  ChatMessagePayload,
  Message,
  DonePayload,
  APIError,
} from '../types';

// Backend response type (not exported from types/index.ts)
interface BackendAuthResponse {
  user: {
    id: string;
    email: string;
    created_at: string;
  };
  tokens: {
    access_token: string;
    token_type: string;
    expires_in: number;
  };
}

// ============================================================================
// Configuration
// ============================================================================

// Use Vite proxy in development (empty VITE_API_URL), direct URL in production
const BASE_URL = import.meta.env.VITE_API_URL || '';
const TOKEN_KEY = 'auth_token';

// ============================================================================
// Token Management
// ============================================================================

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

// ============================================================================
// HTTP Utilities
// ============================================================================

class APIClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = 'Request failed';
      
      try {
        const error: APIError = await response.json();
        
        // Handle FastAPI validation errors (422)
        if (response.status === 422 && error.detail) {
          if (Array.isArray(error.detail)) {
            // Pydantic validation errors array
            errorMessage = error.detail
              .map((err: any) => {
                const field = err.loc?.slice(1).join('.') || 'field';
                return `${field}: ${err.msg}`;
              })
              .join(', ');
          } else if (typeof error.detail === 'string') {
            errorMessage = error.detail;
          } else if (typeof error.detail === 'object') {
            errorMessage = JSON.stringify(error.detail);
          }
        } else if (typeof error.detail === 'string') {
          errorMessage = error.detail;
        }
      } catch (e) {
        // If JSON parsing fails, use status text
        errorMessage = response.statusText || errorMessage;
      }

      throw new Error(errorMessage);
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error: APIError = await response.json().catch(() => ({
        detail: 'Upload failed',
        status: response.status,
      }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }
}

const api = new APIClient();

// ============================================================================
// Auth API
// ============================================================================

export async function login(email: string, password: string): Promise<AuthResponse> {
  const payload: LoginPayload = { email, password };
  const response = await api.post<BackendAuthResponse>('/api/v1/auth/login', payload);
  // Backend returns nested structure: { user, tokens: { access_token, ... } }
  // Map to frontend structure
  return {
    access_token: response.tokens.access_token,
    token_type: response.tokens.token_type,
    user: response.user,
  };
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const payload: RegisterPayload = { email, password };
  const response = await api.post<BackendAuthResponse>('/api/v1/auth/register', payload);
  // Backend returns nested structure: { user, tokens: { access_token, ... } }
  // Map to frontend structure
  return {
    access_token: response.tokens.access_token,
    token_type: response.tokens.token_type,
    user: response.user,
  };
}

export async function refreshToken(): Promise<AuthResponse> {
  const response = await api.post<BackendAuthResponse>('/api/v1/auth/refresh');
  // Backend returns nested structure: { user, tokens: { access_token, ... } }
  // Map to frontend structure
  return {
    access_token: response.tokens.access_token,
    token_type: response.tokens.token_type,
    user: response.user,
  };
}

// ============================================================================
// Documents API
// ============================================================================

export async function uploadDocument(
  payload: DocumentUploadPayload
): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('title', payload.title);
  if (payload.description) {
    formData.append('description', payload.description);
  }

  return api.upload<DocumentResponse>('/api/v1/documents/upload', formData);
}

export async function listDocuments(): Promise<DocumentResponse[]> {
  return api.get<DocumentResponse[]>('/api/v1/documents');
}

export async function getDocument(id: string): Promise<DocumentResponse> {
  return api.get<DocumentResponse>(`/api/v1/documents/${id}`);
}

export async function deleteDocument(id: string): Promise<void> {
  return api.delete<void>(`/api/v1/documents/${id}`);
}

// ============================================================================
// Chat API (Server-Sent Events)
// ============================================================================

export function streamRAGChat(
  messages: Message[],
  documentIds: string[] | undefined,
  onToken: (token: string) => void,
  onDone: (data: DonePayload) => void,
  onError: (err: Error) => void
): () => void {
  let controller: AbortController | null = new AbortController();

  const payload: ChatMessagePayload = {
    messages: messages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      createdAt: m.createdAt,
    })),
    document_ids: documentIds,
    use_rag: !!documentIds && documentIds.length > 0,
  };

  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  fetch(`${BASE_URL}/api/v1/chat/rag-stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const error: APIError = await response.json().catch(() => ({
          detail: 'Stream failed',
          status: response.status,
        }));
        throw new Error(error.detail || 'Stream failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;

          const data = line.slice(6); // Remove "data: " prefix

          if (data === '[DONE]') {
            continue;
          }

          try {
            const parsed = JSON.parse(data);

            if (parsed.type === 'token') {
              onToken(parsed.content);
            } else if (parsed.type === 'done') {
              onDone({
                total_tokens: parsed.data.total_tokens,
                sources: parsed.data.sources,
              });
            } else if (parsed.type === 'error') {
              onError(new Error(parsed.error));
            }
          } catch (e) {
            console.error('Failed to parse SSE message:', e);
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err);
      }
    });

  // Return cleanup function
  return () => {
    if (controller) {
      controller.abort();
      controller = null;
    }
  };
}
