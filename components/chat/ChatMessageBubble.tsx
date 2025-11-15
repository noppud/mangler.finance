'use client'

import type { ChatMessage } from '@/types/chat'
import { IssuesList } from '../features/IssuesList'
import { ModificationResult } from '../features/ModificationResult'
import { CreationResult } from '../features/CreationResult'

interface ChatMessageBubbleProps {
  message: ChatMessage
}

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  // User messages (right-aligned)
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] px-4 py-3 bg-blue-600 text-white rounded-2xl rounded-tr-sm">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    )
  }

  // Assistant messages (left-aligned)
  if (message.role === 'assistant') {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[80%] px-4 py-3 bg-gray-800 text-gray-100 rounded-2xl rounded-tl-sm border border-gray-700">
          {message.metadata?.error ? (
            <div className="flex items-start gap-2">
              <span className="text-red-400 text-lg">⚠️</span>
              <div>
                <p className="font-semibold text-red-400 mb-1">Error</p>
                <p className="whitespace-pre-wrap break-words text-gray-300">{message.content}</p>
              </div>
            </div>
          ) : (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          )}
        </div>
      </div>
    )
  }

  // Tool messages (full-width rich content)
  if (message.role === 'tool') {
    return (
      <div className="mb-6">
        {message.metadata?.toolName === 'detect_issues' && (
          <IssuesList result={message.metadata.payload as any} />
        )}
        {message.metadata?.toolName === 'modify_sheet' && (
          <ModificationResult result={message.metadata.payload as any} />
        )}
        {message.metadata?.toolName === 'create_sheet' && (
          <CreationResult result={message.metadata.payload as any} />
        )}
      </div>
    )
  }

  // System messages (centered, subtle)
  if (message.role === 'system') {
    return (
      <div className="flex justify-center mb-4">
        <div className="px-4 py-2 bg-gray-800/50 text-gray-400 text-sm rounded-lg border border-gray-700/50">
          {message.content}
        </div>
      </div>
    )
  }

  return null
}
