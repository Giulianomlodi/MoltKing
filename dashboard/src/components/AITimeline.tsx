import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { LogEntry } from "@/hooks/useWebSocket"

interface AITimelineProps {
  logs: LogEntry[]
}

function threatColor(level: string): string {
  switch (level) {
    case "critical": return "bg-red-600"
    case "high": return "bg-orange-500"
    case "medium": return "bg-yellow-500 text-black"
    case "low": return "bg-emerald-600"
    default: return "bg-muted"
  }
}

function economyColor(status: string): string {
  switch (status) {
    case "booming": return "bg-emerald-600"
    case "growing": return "bg-emerald-500"
    case "stable": return "bg-blue-500"
    case "declining": return "bg-yellow-500 text-black"
    case "critical": return "bg-red-600"
    default: return "bg-muted"
  }
}

function ParamDiff({ recs }: { recs: Record<string, unknown> }) {
  if (!recs || Object.keys(recs).length === 0) return null
  const fields = ["worker_cap", "soldier_cap", "tower_cap", "priority_mode", "spawn_energy_reserve"] as const
  const diffs: { key: string; val: unknown }[] = []
  for (const f of fields) {
    if (recs[f] != null) {
      diffs.push({ key: f, val: recs[f] })
    }
  }
  if (diffs.length === 0) return null
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {diffs.map(({ key, val }) => (
        <span key={key} className="rounded bg-accent px-1.5 py-0.5 font-mono text-xs">
          {key}: <span className="text-emerald-400">{String(val)}</span>
        </span>
      ))}
    </div>
  )
}

function EntryCard({ entry }: { entry: LogEntry }) {
  const a = entry.analysis
  const isFailed = a.threat_level === "unknown" || a.situation_assessment === "Analysis failed"
  const hasChanges = Object.keys(a.recommendations || {}).length > 0 && !isFailed

  return (
    <div className={`rounded-lg border p-3 ${isFailed ? "border-muted opacity-50" :
        hasChanges ? "border-emerald-500/50" :
          "border-border"
      }`}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-mono">{entry.timestamp}</span>
        <span>Tick {entry.state.tick}</span>
        <Badge className={`${threatColor(a.threat_level)} text-xs`}>
          {a.threat_level}
        </Badge>
        <Badge className={`${economyColor(a.economy_status)} text-xs`}>
          {a.economy_status}
        </Badge>
        <span className="ml-auto text-xs">
          {entry.state.units.workers}w / {entry.state.units.soldiers}s / {entry.state.threats.enemy_units}e
        </span>
      </div>

      {!isFailed && (
        <>
          <p className="mt-2 text-sm">{a.situation_assessment}</p>

          <div className="mt-2 rounded bg-muted/50 p-2">
            <span className="text-xs font-semibold text-muted-foreground">REASONING</span>
            <p className="mt-0.5 text-sm text-muted-foreground">{a.reasoning}</p>
          </div>

          {a.suggestion_evaluation && (
            <div className="mt-2 rounded border border-blue-500/50 bg-blue-500/10 p-2">
              <span className="text-xs font-semibold text-blue-400">OPERATOR SUGGESTION EVAL</span>
              <p className="mt-0.5 text-sm text-muted-foreground">{a.suggestion_evaluation}</p>
            </div>
          )}

          <ParamDiff recs={a.recommendations} />

          {a.immediate_actions.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">
              {a.immediate_actions.map((action, i) => (
                <li key={i} className="flex gap-1">
                  <span className="text-emerald-400">-</span> {action}
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {isFailed && (
        <p className="mt-1 text-xs text-red-400">{a.reasoning}</p>
      )}
    </div>
  )
}

export default function AITimeline({ logs }: AITimelineProps) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          AI Decision Timeline
          <Badge variant="secondary" className="text-xs">{logs.length} entries</Badge>
        </CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-[600px]">
          <div className="space-y-2 p-3">
            {logs.length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No AI decisions yet. Start the AI service to see analysis.
              </p>
            )}
            {logs.map((entry, i) => (
              <EntryCard key={`${entry.timestamp}-${i}`} entry={entry} />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
