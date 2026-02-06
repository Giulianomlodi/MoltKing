import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import type { GameState } from "@/hooks/useWebSocket"
import LlmSettings from "@/components/LlmSettings"

interface HeaderProps {
  state: GameState
  connected: boolean
  send: (msg: Record<string, unknown>) => void
}

function formatUptime(seconds: number | null): string {
  if (seconds == null) return ""
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

export default function Header({ state, connected, send }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold tracking-tight">MoltKing Command Center</h1>
          <Badge variant={connected ? "default" : "destructive"} className="text-xs">
            {connected ? "LIVE" : "DISCONNECTED"}
          </Badge>
        </div>

        <div className="flex items-center gap-4">
          {/* Game info */}
          {state.tick != null && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Tick <span className="font-mono text-foreground">{state.tick}</span></span>
              {state.agent && (
                <span>Lv.<span className="font-mono text-foreground">{state.agent.level}</span></span>
              )}
            </div>
          )}

          {/* Bot controls */}
          <div className="flex items-center gap-2">
            <Badge variant={state.botRunning ? "default" : "secondary"} className={state.botRunning ? "bg-emerald-600" : ""}>
              Bot {state.botRunning ? "ON" : "OFF"}
            </Badge>
            {state.botRunning && state.botUptime != null && (
              <span className="text-xs text-muted-foreground">{formatUptime(state.botUptime)}</span>
            )}
            {state.botRunning ? (
              <Button size="sm" variant="destructive" onClick={() => send({ type: "bot_stop" })}>
                Stop Bot
              </Button>
            ) : (
              <Button size="sm" variant="default" onClick={() => send({ type: "bot_start" })}>
                Start Bot
              </Button>
            )}
          </div>

          {/* AI controls */}
          <div className="flex items-center gap-2">
            <Badge variant={state.aiRunning ? "default" : "secondary"} className={state.aiRunning ? "bg-blue-600" : ""}>
              AI {state.aiRunning ? "ON" : "OFF"}
            </Badge>
            {state.llmConfig && (
              <span className="text-xs text-muted-foreground font-mono">
                {state.llmConfig.model.split("-").slice(0, 2).join("-")}
              </span>
            )}
            {state.aiRunning && state.aiUptime != null && (
              <span className="text-xs text-muted-foreground">{formatUptime(state.aiUptime)}</span>
            )}
            {state.aiRunning ? (
              <Button size="sm" variant="destructive" onClick={() => send({ type: "ai_stop" })}>
                Stop AI
              </Button>
            ) : (
              <Button size="sm" variant="default" onClick={() => send({ type: "ai_start" })}>
                Start AI
              </Button>
            )}
          </div>

          <Separator orientation="vertical" className="h-6" />
          <LlmSettings aiRunning={state.aiRunning} />
        </div>
      </div>
    </header>
  )
}
