const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

/**
 * Send a message to the tutor.
 * @param {Array}  messages  [{role, content}, ...]
 * @param {string} topic     Current study topic
 * @param {string|null} provider  Force a specific LLM ("claude"|"openai"|"gemini")
 * @returns {{ reply: string, provider_used: string }}
 */
export async function sendMessage(messages, topic = "", provider = null) {
  const res = await fetch(`${BASE}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      topic,
      ...(provider && { provider }),
    }),
  })
  if (!res.ok) throw new Error(`Chat API error: ${res.status}`)
  return res.json()
}

/**
 * Generate a quiz on a topic.
 * @returns {{ topic: string, questions: Array }}
 */
export async function getQuiz(topic, numQuestions = 5) {
  const res = await fetch(`${BASE}/quiz/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, num_questions: numQuestions }),
  })
  if (!res.ok) throw new Error(`Quiz API error: ${res.status}`)
  return res.json()
}

/** Check backend health and active LLM. */
export async function healthCheck() {
  const res = await fetch(`${BASE}/health`)
  return res.json()
}
