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

// Uptime formatter removed as it's not currently used in the compact mobile layout

export default function Header({ state, connected, send }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex flex-col md:flex-row items-center justify-between px-4 py-3 md:py-2 gap-3 md:gap-0">
        <div className="flex items-center justify-between w-full md:w-auto gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold tracking-tight">
              <span className="hidden sm:inline">MoltKing Command Center</span>
              <span className="sm:hidden">MoltKing</span>
            </h1>
            <Badge variant={connected ? "default" : "destructive"} className="text-[10px] md:text-xs">
              {connected ? "LIVE" : "OFFLINE"}
            </Badge>
          </div>
          <div className="md:hidden flex items-center gap-2">
            <LlmSettings aiRunning={state.aiRunning} />
          </div>
        </div>

        <div className="flex items-center gap-2 md:gap-4 flex-wrap justify-center md:justify-end w-full md:w-auto">
          {/* Game info */}
          {state.tick != null && (
            <div className="flex items-center gap-2 text-xs md:text-sm text-muted-foreground mr-1">
              <span>T:<span className="font-mono text-foreground">{state.tick}</span></span>
              {state.agent && (
                <span>L:<span className="font-mono text-foreground">{state.agent.level}</span></span>
              )}
            </div>
          )}

          {/* Bot controls */}
          <div className="flex items-center gap-1.5 border-r border-border pr-2 md:pr-0 md:border-0">
            <Badge variant={state.botRunning ? "default" : "secondary"} className={`${state.botRunning ? "bg-emerald-600" : ""} text-[10px] md:text-xs px-1.5`}>
              Bot {state.botRunning ? "ON" : "OFF"}
            </Badge>
            {state.botRunning ? (
              <Button size="icon" variant="destructive" className="h-7 w-7 md:h-8 md:w-auto md:px-3" onClick={() => send({ type: "bot_stop" })}>
                <span className="hidden md:inline">Stop</span>
                <span className="md:hidden">■</span>
              </Button>
            ) : (
              <Button size="icon" variant="default" className="h-7 w-7 md:h-8 md:w-auto md:px-3" onClick={() => send({ type: "bot_start" })}>
                <span className="hidden md:inline">Start</span>
                <span className="md:hidden">▶</span>
              </Button>
            )}
          </div>

          {/* AI controls */}
          <div className="flex items-center gap-1.5">
            <Badge variant={state.aiRunning ? "default" : "secondary"} className={`${state.aiRunning ? "bg-blue-600" : ""} text-[10px] md:text-xs px-1.5`}>
              AI {state.aiRunning ? "ON" : "OFF"}
            </Badge>
            {state.llmConfig && (
              <span className="hidden sm:inline text-xs text-muted-foreground font-mono">
                {state.llmConfig.model.split("-").slice(0, 2).join("-")}
              </span>
            )}
            {state.aiRunning ? (
              <Button size="icon" variant="destructive" className="h-7 w-7 md:h-8 md:w-auto md:px-3" onClick={() => send({ type: "ai_stop" })}>
                <span className="hidden md:inline">Stop AI</span>
                <span className="md:hidden">■</span>
              </Button>
            ) : (
              <Button size="icon" variant="default" className="h-7 w-7 md:h-8 md:w-auto md:px-3" onClick={() => send({ type: "ai_start" })}>
                <span className="hidden md:inline">Start AI</span>
                <span className="md:hidden">▶</span>
              </Button>
            )}
          </div>

          <div className="hidden md:flex items-center gap-4">
            <Separator orientation="vertical" className="h-6" />
            <LlmSettings aiRunning={state.aiRunning} />
          </div>
        </div>
      </div>
    </header>
  )
}
