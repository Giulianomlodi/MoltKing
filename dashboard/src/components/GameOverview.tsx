import { Card, CardContent } from "@/components/ui/card"
import type { GameState } from "@/hooks/useWebSocket"

interface GameOverviewProps {
  state: GameState
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className="h-2 w-full rounded-full bg-muted">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function Metric({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xl font-bold font-mono">{value}</span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  )
}

export default function GameOverview({ state }: GameOverviewProps) {
  const workerCap = state.params.worker_cap ?? 120
  const soldierCap = state.params.soldier_cap ?? 100
  const mode = state.params.priority_mode ?? "balanced"

  return (
    <Card>
      <CardContent className="py-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
          <Metric label="Workers" value={state.units.workers} sub={`/ ${workerCap} cap`} />
          <Metric label="Soldiers" value={state.units.soldiers} sub={`/ ${soldierCap} cap`} />
          <Metric label="Healers" value={state.units.healers} />
          <Metric label="Spawns" value={state.structures.spawns} />
          <Metric label="Towers" value={state.structures.towers} />
          <Metric label="Spawn Energy" value={state.structures.spawnEnergy} />
          <Metric label="Enemies" value={state.threats.enemyUnits} />
        </div>

        <div className="mt-3 grid grid-cols-2 gap-4">
          <div>
            <div className="mb-1 flex justify-between text-xs text-muted-foreground">
              <span>Workers</span>
              <span>{state.units.workers} / {workerCap}</span>
            </div>
            <ProgressBar value={state.units.workers} max={workerCap} color="bg-emerald-500" />
          </div>
          <div>
            <div className="mb-1 flex justify-between text-xs text-muted-foreground">
              <span>Soldiers</span>
              <span>{state.units.soldiers} / {soldierCap}</span>
            </div>
            <ProgressBar value={state.units.soldiers} max={soldierCap} color="bg-red-500" />
          </div>
        </div>

        <div className="mt-2 text-center">
          <span className="text-xs text-muted-foreground">Priority: </span>
          <span className={`text-xs font-semibold ${
            mode === "military" ? "text-red-400" :
            mode === "economy" ? "text-emerald-400" :
            mode === "defense" ? "text-yellow-400" :
            "text-blue-400"
          }`}>
            {mode.toUpperCase()}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
