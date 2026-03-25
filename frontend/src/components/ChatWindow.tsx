import { useState, useEffect, useRef, FormEvent } from 'react'
import { askQuestion, getChatHistory } from '../api/chat'
import type { ChatMessage, SourceChunk } from '../types'

interface Props {
  packageId: string
}

export function ChatWindow({ packageId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getChatHistory(packageId)
      .then(setMessages)
      .catch(() => {})
  }, [packageId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!question.trim() || loading) return
    const q = question.trim()
    setQuestion('')
    setError('')
    setLoading(true)

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: q,
      sources: null,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      const resp = await askQuestion(packageId, q)
      const assistantMsg: ChatMessage = {
        id: resp.message_id,
        role: 'assistant',
        content: resp.answer,
        sources: resp.sources,
        created_at: resp.created_at,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      setError('Не удалось получить ответ. Попробуйте ещё раз.')
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[560px] bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-gray-400 mt-8">
            Задайте вопрос по документу
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-sm'
                : 'bg-gray-100 text-gray-900 rounded-bl-sm'
            }`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <details className="mt-2">
                  <summary className="text-xs opacity-60 cursor-pointer">
                    Источники ({msg.sources.length})
                  </summary>
                  <div className="mt-1 space-y-1">
                    {msg.sources.map((s: SourceChunk, i: number) => (
                      <p key={i} className="text-xs opacity-70 border-l-2 border-current pl-2">
                        {s.text.slice(0, 120)}…
                      </p>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-gray-500">
              Думаю...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-red-50 text-xs text-red-600 border-t border-red-100">
          {error}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2 p-3 border-t border-gray-200">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Задайте вопрос по договору..."
          disabled={loading}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
        >
          →
        </button>
      </form>
    </div>
  )
}
