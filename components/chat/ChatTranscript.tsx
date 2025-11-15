'use client'

import { useEffect, useRef } from 'react'
import type { ChatMessage } from '@/types/chat'
import { ChatMessageBubble } from './ChatMessageBubble'

interface ChatTranscriptProps {
  messages: ChatMessage[]
  isLoading?: boolean
}

export function ChatTranscript({ messages, isLoading = false }: ChatTranscriptProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4">
        <div className="mb-6 text-6xl">📊</div>
        <h2 className="text-2xl font-bold text-gray-100 mb-2">Welcome to Sheet Mangler</h2>
        <p className="text-gray-400 max-w-md">
          I can help you detect issues, modify sheets, and create new spreadsheets. Just tell me what you need!
        </p>
        <div className="mt-8 space-y-2 text-left bg-gray-800/50 border border-gray-700 rounded-lg p-4 max-w-md">
          <p className="text-sm text-gray-300 font-semibold mb-2">Try asking:</p>
          <p className="text-sm text-gray-400">"Check my sheet for issues"</p>
          <p className="text-sm text-gray-400">"Add a Total column"</p>
          <p className="text-sm text-gray-400">"Create a budget tracker"</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1">
      {messages.map((message) => (
        <ChatMessageBubble key={message.id} message={message} />
      ))}

      {isLoading && (
        <div className="flex justify-start mb-4">
          <div className="px-4 py-3 bg-gray-800 text-gray-100 rounded-2xl rounded-tl-sm border border-gray-700">
            <div className="flex gap-1 items-center">
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div
                className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                style={{ animationDelay: '150ms' }}
              />
              <div
                className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                style={{ animationDelay: '300ms' }}
              />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
