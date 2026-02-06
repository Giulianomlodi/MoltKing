import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import type { GameState } from "@/hooks/useWebSocket"

interface HumanSuggestionProps {
  state: GameState
  send: (msg: Record<string, unknown>) => void
}

export default function HumanSuggestion({ state, send }: HumanSuggestionProps) {
  const [draft, setDraft] = useState("")
  const active = state.humanSuggestion

  const handleSend = () => {
    const text = draft.trim()
    if (!text) return
    send({ type: "human_suggestion", suggestion: text })
    setDraft("")
  }

  const handleClear = () => {
    send({ type: "clear_suggestion" })
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          Operator Suggestion
          {active ? (
            <Badge className="bg-emerald-600 text-xs">Active</Badge>
          ) : (
            <Badge variant="secondary" className="text-xs">No suggestion</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="pt-3">
        {active && (
          <div className="mb-3 rounded-lg border border-emerald-500/50 p-3">
            <p className="text-sm">{active.suggestion}</p>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Sent {active.timestamp}
              </span>
              <Button variant="destructive" size="xs" onClick={handleClear}>
                Clear
              </Button>
            </div>
          </div>
        )}
        <div className="flex gap-2">
          <textarea
            className="flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            rows={2}
            placeholder="Type a strategic suggestion for the AI..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSend()
            }}
          />
          <Button
            size="sm"
            className="self-end"
            disabled={!draft.trim()}
            onClick={handleSend}
          >
            Send to AI
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
