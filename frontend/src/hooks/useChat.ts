import { useState, useCallback, useRef } from "react"
import { streamRAGChat } from "../lib/api"
import type { Message, Source } from "../types"

interface UseChatReturn {
  messages: Message[]
  loading: boolean
  error: string | null
  sources: Source[]
  send: (text: string) => Promise<void>
  reset: () => void
  stopStreaming: () => void
}

/**
 * Manages a full tutor conversation with SSE streaming.
 * @param documentIds  Document IDs for RAG context
 */
export function useChat(documentIds: string[] = []): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const abortRef = useRef<(() => void) | null>(null)

  const send = useCallback(
    async (text: string) => {
      if (!text.trim()) return

      // Add user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        createdAt: new Date(),
      }

      setMessages((prev) => [...prev, userMsg])
      setLoading(true)
      setError(null)
      setSources([])

      // Add assistant message placeholder with streaming flag
      const assistantId = crypto.randomUUID()
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date(),
        isStreaming: true,
      }

      setMessages((prev) => [...prev, assistantMsg])

      // Start SSE stream
      const allMessages = [...messages, userMsg]
      
      abortRef.current = streamRAGChat(
        allMessages,
        documentIds.length > 0 ? documentIds : undefined,
        // onToken: append to assistant message content
        (token: string) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + token }
                : m
            )
          )
        },
        // onDone: stop streaming, save sources
        (data: { sources?: Source[] }) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, isStreaming: false, sources: data.sources }
                : m
            )
          )
          setSources(data.sources || [])
          setLoading(false)
        },
        // onError: display error
        (err: Error) => {
          setError(err.message)
          // Remove the failed assistant message
          setMessages((prev) => prev.filter((m) => m.id !== assistantId))
          setLoading(false)
        }
      )
    },
    [messages, documentIds]
  )

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current()
      abortRef.current = null
    }
    setMessages([])
    setError(null)
    setSources([])
  }, [])

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current()
      abortRef.current = null
    }
    setLoading(false)
    // Mark streaming message as complete
    setMessages((prev) =>
      prev.map((m) =>
        m.isStreaming ? { ...m, isStreaming: false } : m
      )
    )
  }, [])

  return { messages, loading, error, sources, send, reset, stopStreaming }
}
