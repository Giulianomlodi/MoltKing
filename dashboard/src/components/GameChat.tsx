import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { ChatMessage } from "@/hooks/useWebSocket"

interface GameChatProps {
  messages: ChatMessage[]
  myName?: string
}

function formatTime(epochMs: number): string {
  const d = new Date(epochMs)
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
}

export default function GameChat({ messages, myName = "MoltKing" }: GameChatProps) {
  // API returns newest first; display oldest-first (chronological)
  const sorted = [...messages].reverse()

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          Game Chat
          <Badge variant="secondary" className="text-xs">{messages.length} messages</Badge>
        </CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-[400px]">
          <div className="space-y-1.5 p-3">
            {sorted.length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No chat messages yet.
              </p>
            )}
            {sorted.map((msg, i) => {
              const isMine = msg.senderName === myName
              return (
                <div
                  key={`${msg.createdAt}-${i}`}
                  className={`rounded px-2.5 py-1.5 text-sm ${
                    isMine
                      ? "border border-emerald-500/40 bg-emerald-500/10"
                      : "bg-muted/50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold ${isMine ? "text-emerald-400" : "text-blue-400"}`}>
                      {msg.senderName}
                    </span>
                    {isMine && (
                      <Badge className="bg-emerald-600 text-[10px] px-1 py-0 leading-tight">AI</Badge>
                    )}
                    <span className="ml-auto text-[10px] text-muted-foreground font-mono">
                      {formatTime(msg.createdAt)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-muted-foreground break-words">{msg.message}</p>
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
