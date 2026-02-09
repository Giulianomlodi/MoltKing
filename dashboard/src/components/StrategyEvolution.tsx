import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts"
import type { LogEntry } from "@/hooks/useWebSocket"

interface StrategyEvolutionProps {
  logs: LogEntry[]
}

export default function StrategyEvolution({ logs }: StrategyEvolutionProps) {
  // Logs come newest-first, reverse for charts
  const chronological = [...logs].reverse()

  let lastRecs: Record<string, any> = {}

  const paramData = chronological.map((e, i) => {
    const recs = e.analysis.recommendations
    if (recs && Object.keys(recs).length > 0) {
      lastRecs = { ...recs }
    }
    return {
      idx: i,
      tick: e.state.tick,
      worker_cap: lastRecs.worker_cap as number | undefined,
      soldier_cap: lastRecs.soldier_cap as number | undefined,
      tower_cap: lastRecs.tower_cap as number | undefined,
    }
  })

  const unitData = chronological.map((e, i) => ({
    idx: i,
    tick: e.state.tick,
    workers: e.state.units.workers,
    soldiers: e.state.units.soldiers,
    enemies: e.state.threats.enemy_units,
  }))

  const energyData = chronological.map((e, i) => ({
    idx: i,
    tick: e.state.tick,
    spawnEnergy: e.state.structures.total_spawn_energy,
    sourceEnergy: Math.round((e.state.economy?.total_source_energy ?? 0) / 100),
  }))

  // Also reset for modeData
  let lastMode = "balanced"
  const modeData = chronological.map((e, i) => {
    const mode = e.analysis.recommendations?.priority_mode as string
    if (mode) {
      lastMode = mode
    }
    return {
      idx: i,
      tick: e.state.tick,
      mode: lastMode,
    }
  })

  const tickFormatter = (idx: number) => {
    const d = paramData[idx]
    return d ? String(d.tick) : ""
  }

  if (logs.length < 2) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Strategy Evolution</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-8 text-center text-sm text-muted-foreground">
            Need at least 2 AI decisions to show charts.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Strategy Evolution</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Cap recommendations over time */}
        <div>
          <h3 className="mb-2 text-xs font-semibold text-muted-foreground">RECOMMENDED CAPS</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={paramData}>
              <XAxis dataKey="idx" tickFormatter={tickFormatter} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                labelFormatter={(idx) => `Tick ${paramData[idx as number]?.tick}`}
                contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="worker_cap" stroke="#10b981" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="soldier_cap" stroke="#ef4444" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="tower_cap" stroke="#eab308" strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Actual units over time */}
        <div>
          <h3 className="mb-2 text-xs font-semibold text-muted-foreground">UNIT COUNTS</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={unitData}>
              <XAxis dataKey="idx" tickFormatter={tickFormatter} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                labelFormatter={(idx) => `Tick ${unitData[idx as number]?.tick}`}
                contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="workers" stroke="#10b981" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="soldiers" stroke="#ef4444" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="enemies" stroke="#f97316" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Energy over time */}
        <div>
          <h3 className="mb-2 text-xs font-semibold text-muted-foreground">SPAWN ENERGY</h3>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={energyData}>
              <XAxis dataKey="idx" tickFormatter={tickFormatter} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                labelFormatter={(idx) => `Tick ${energyData[idx as number]?.tick}`}
                contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
              />
              <Area type="monotone" dataKey="spawnEnergy" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Priority mode timeline */}
        <div>
          <h3 className="mb-2 text-xs font-semibold text-muted-foreground">PRIORITY MODE</h3>
          <div className="flex h-6 w-full overflow-hidden rounded">
            {modeData.map((d, i) => {
              const color =
                d.mode === "military" ? "bg-red-500" :
                  d.mode === "economy" ? "bg-emerald-500" :
                    d.mode === "defense" ? "bg-yellow-500" :
                      "bg-blue-500"
              return (
                <div
                  key={i}
                  className={`flex-1 ${color}`}
                  title={`Tick ${d.tick}: ${d.mode}`}
                />
              )
            })}
          </div>
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <div className="flex gap-3">
              <span><span className="inline-block h-2 w-2 rounded-full bg-blue-500" /> balanced</span>
              <span><span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> economy</span>
              <span><span className="inline-block h-2 w-2 rounded-full bg-red-500" /> military</span>
              <span><span className="inline-block h-2 w-2 rounded-full bg-yellow-500" /> defense</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
