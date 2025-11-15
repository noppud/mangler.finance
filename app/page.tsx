'use client'

import { useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { ChatTranscript } from '@/components/chat/ChatTranscript'
import { ChatInput } from '@/components/chat/ChatInput'
import { Input } from '@/components/ui/Input'
import type { ChatMessage, SheetContext } from '@/types/chat'

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sheetContext, setSheetContext] = useState<SheetContext>({
    spreadsheetId: '',
    sheetTitle: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [showContextPanel, setShowContextPanel] = useState(true)

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: 'user',
      content,
    }

    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setIsLoading(true)

    try {
      // Call the chat API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: updatedMessages,
          sheetContext,
        }),
      })

      if (!response.ok) {
        let errorMessage = 'Failed to process your request'
        try {
          const errorData = await response.json()
          if (errorData.error) {
            errorMessage = errorData.error
            if (errorData.details) {
              errorMessage += `: ${errorData.details}`
            }
          }
        } catch {
          // Ignore JSON parse errors
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()

      // Append assistant response messages
      if (data.messages && Array.isArray(data.messages)) {
        setMessages([...updatedMessages, ...data.messages])
      }
    } catch (error) {
      console.error('Error sending message:', error)

      // Add error message
      const errorMessage: ChatMessage = {
        id: uuidv4(),
        role: 'assistant',
        content: error instanceof Error ? error.message : 'An unexpected error occurred',
        metadata: {
          error: error instanceof Error ? error.message : 'Unknown error',
        },
      }
      setMessages([...updatedMessages, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleResetConversation = () => {
    if (confirm('Are you sure you want to reset the conversation? This cannot be undone.')) {
      setMessages([])
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-gray-900/95 backdrop-blur border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-2xl bg-blue-600 text-white flex items-center justify-center text-sm font-semibold shadow-sm">
              SM
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-100 tracking-tight">Sheet Mangler</h1>
              <p className="text-sm text-gray-400">AI-powered Google Sheets assistant</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowContextPanel(!showContextPanel)}
              className="px-3 py-1.5 text-sm text-gray-300 hover:text-gray-100 hover:bg-gray-800 rounded-lg transition-colors"
            >
              {showContextPanel ? 'Hide' : 'Show'} Sheet Context
            </button>
            {messages.length > 0 && (
              <button
                onClick={handleResetConversation}
                className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-gray-800 rounded-lg transition-colors"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main content area */}
      <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto">
        {/* Sheet Context Panel */}
        {showContextPanel && (
          <div className="px-4 pt-4">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-100">Sheet Context</h3>
                <span className="text-xs text-gray-500">Optional - fill this in for sheet operations</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Input
                  label="Spreadsheet URL or ID"
                  placeholder="https://docs.google.com/spreadsheets/d/... or just the ID"
                  value={sheetContext.spreadsheetId || ''}
                  onChange={(e) =>
                    setSheetContext({
                      ...sheetContext,
                      spreadsheetId: e.target.value,
                    })
                  }
                />
                <Input
                  label="Sheet Title (tab name)"
                  placeholder="Sheet1"
                  value={sheetContext.sheetTitle || ''}
                  onChange={(e) =>
                    setSheetContext({
                      ...sheetContext,
                      sheetTitle: e.target.value,
                    })
                  }
                />
              </div>
            </div>
          </div>
        )}

        {/* Chat Transcript */}
        <div className="flex-1 overflow-hidden">
          <ChatTranscript messages={messages} isLoading={isLoading} />
        </div>

        {/* Chat Input */}
        <div className="px-4 pb-4 pt-2 bg-gray-900">
          <div className="max-w-4xl mx-auto">
            <ChatInput
              onSend={handleSendMessage}
              disabled={isLoading}
              placeholder={
                messages.length === 0
                  ? 'Ask me to detect issues, modify a sheet, or create a new spreadsheet...'
                  : 'Type your message...'
              }
            />
            <p className="text-xs text-gray-500 mt-2 text-center">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 bg-gray-900/95">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
          <p>Built with Next.js, OpenRouter, and Google Sheets API</p>
        </div>
      </footer>
    </div>
  )
}
