import { useState, useRef, useEffect } from "react"
import { api } from "@/lib/api"
import { useAuth } from "@/contexts/AuthContext"
import { Layout } from "@/components/Layout"
import { Card, CardContent } from "@/components/ui/card"
import { ChatMessage } from "@/components/ChatMessage"
import { ChatInput } from "@/components/ChatInput"
import { Sparkles } from "lucide-react"
import type { ChatResponse } from "@/types"

interface Message {
  role: "user" | "assistant"
  content: string
  citations?: Array<{ id: string; title: string; relevance: number }>
}

export default function ChatPage() {
  const { activeWorkspaceId } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async (text: string) => {
    if (!activeWorkspaceId) return

    const userMsg: Message = { role: "user", content: text }
    setMessages(prev => [...prev, userMsg])
    setSending(true)

    try {
      const res = await api.post<ChatResponse>("/v1/chat", {
        workspace_id: activeWorkspaceId,
        message: text,
        conversation_id: conversationId || undefined,
      })
      setConversationId(res.conversation_id)
      setMessages(prev => [...prev, {
        role: "assistant",
        content: res.answer,
        citations: res.citations,
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: err instanceof Error ? err.message : "Sorry, I couldn't process that question.",
      }])
    } finally {
      setSending(false)
    }
  }

  return (
    <Layout title="Chat">
      <Card className="flex flex-col h-[calc(100vh-10rem)]">
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
              <Sparkles className="h-12 w-12 mb-4 opacity-30" />
              <p className="text-sm mb-1">Ask questions about your knowledge base</p>
              <p className="text-xs">The AI will search your concepts and provide answers with citations</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <ChatMessage key={i} role={msg.role} content={msg.content} citations={msg.citations} />
            ))
          )}
          <div ref={bottomRef} />
        </CardContent>
        <div className="border-t p-4">
          <ChatInput onSend={handleSend} disabled={sending || !activeWorkspaceId} />
        </div>
      </Card>
    </Layout>
  )
}
