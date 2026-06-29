import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Bot, User, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"

interface Citation {
  id: string
  title: string
  relevance: number
}

interface ChatMessageProps {
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
}

export function ChatMessage({ role, content, citations }: ChatMessageProps) {
  const navigate = useNavigate()

  return (
    <div className={cn("flex gap-3", role === "user" ? "flex-row-reverse" : "")}>
      <div className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
        role === "assistant" ? "bg-primary text-primary-foreground" : "bg-muted"
      )}>
        {role === "assistant" ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
      </div>
      <div className={cn(
        "flex flex-col gap-2 max-w-[80%]",
        role === "user" ? "items-end" : "items-start"
      )}>
        <div className={cn(
          "rounded-lg px-4 py-2 text-sm whitespace-pre-wrap leading-relaxed",
          role === "assistant"
            ? "bg-muted"
            : "bg-primary text-primary-foreground"
        )}>
          {content}
        </div>
        {citations && citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {citations.map(c => (
              <Button
                key={c.id}
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={() => navigate(`/concept/${c.id}`)}
              >
                <ExternalLink className="h-3 w-3" />
                {c.title.length > 30 ? c.title.slice(0, 30) + "..." : c.title}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
