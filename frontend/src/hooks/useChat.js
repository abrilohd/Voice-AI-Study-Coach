import { useState, useCallback } from "react"
import { sendMessage } from "../api/client"

/**
 * Manages a full tutor conversation.
 * @param {string} topic  Study topic passed to the backend
 */
export function useChat(topic) {
  const [messages, setMessages]         = useState([])
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [lastProvider, setLastProvider] = useState(null)

  const send = useCallback(
    async (text, provider = null) => {
      if (!text.trim()) return
      const userMsg = { role: "user", content: text }
      const next    = [...messages, userMsg]
      setMessages(next)
      setLoading(true)
      setError(null)
      try {
        const data = await sendMessage(next, topic, provider)
        setMessages([...next, { role: "assistant", content: data.reply }])
        setLastProvider(data.provider_used)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    },
    [messages, topic]
  )

  const reset = useCallback(() => {
    setMessages([])
    setError(null)
    setLastProvider(null)
  }, [])

  return { messages, loading, error, lastProvider, send, reset }
}
