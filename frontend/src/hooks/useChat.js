import { useState, useCallback, useRef } from "react"
import { streamRAGChat } from "../lib/api"

/**
 * Manages a full tutor conversation with SSE streaming.
 * @param {string[]} documentIds  Document IDs for RAG context
 */
export function useChat(documentIds = []) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sources, setSources] = useState([])
  const abortRef = useRef(null)

  const send = useCallback(
    async (text) => {
      if (!text.trim()) return

      // Add user message
      const userMsg = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        createdAt: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, userMsg])
      setLoading(true)
      setError(null)
      setSources([])

      // Add assistant message placeholder with streaming flag
      const assistantId = crypto.randomUUID()
      const assistantMsg = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        isStreaming: true,
      }

      setMessages((prev) => [...prev, assistantMsg])

      // Start SSE stream
      const allMessages = [...messages, userMsg]
      
      abortRef.current = streamRAGChat(
        allMessages,
        documentIds.length > 0 ? documentIds : undefined,
        // onToken: append to assistant message content
        (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + token }
                : m
            )
          )
        },
        // onDone: stop streaming, save sources
        (data) => {
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
        (err) => {
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
