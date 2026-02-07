import { useEffect, useRef, useState, useCallback } from "react"

export interface GameState {
  botRunning: boolean
  botPid: number | null
  botUptime: number | null
  aiRunning: boolean
  aiPid: number | null
  aiUptime: number | null
  tick: number | null
  agent: { id: string; name: string; level: number } | null
  units: { workers: number; soldiers: number; healers: number; total: number }
  structures: { spawns: number; towers: number; storages: number; spawnEnergy: number }
  threats: { enemyUnits: number }
  params: StrategyParams
  llmConfig: LlmConfigSummary | null
  mapChunks: MapChunk[]
  humanSuggestion: { suggestion: string; timestamp: string } | null
  chatMessages: ChatMessage[]
}

export interface ChatMessage {
  senderName: string
  message: string
  createdAt: number
}

export interface StrategyParams {
  worker_cap?: number
  soldier_cap?: number
  tower_cap?: number
  priority_mode?: string
  spawn_energy_reserve?: number
  worker_harvest_threshold?: number
  soldier_patrol_distance?: number
}

export interface LogEntry {
  timestamp: string
  state: {
    tick: number
    level: number
    units: { workers: number; soldiers: number; healers: number; total: number; workers_carrying_energy: number; total_worker_energy: number }
    structures: { spawns: number; towers: number; storages: number; construction_sites: number; spawn_energies: number[]; total_spawn_energy: number }
    threats: { enemy_units: number; enemy_structures: number; enemy_types: Record<string, number> }
    economy: { visible_sources: number; sources_with_energy: number; total_source_energy: number }
  }
  analysis: {
    situation_assessment: string
    threat_level: string
    economy_status: string
    recommendations: Record<string, unknown>
    reasoning: string
    suggestion_evaluation?: string
    immediate_actions: string[]
  }
}

export interface LlmConfigSummary {
  provider: string
  model: string
  hasKey: boolean
}

export interface MapChunk {
  x: number
  y: number
  terrain: string[][]
  sources: { x: number; y: number; energy: number }[]
  units: { x: number; y: number; type: string; ownerId: string; hp: number; energy: number }[]
  structures: { x: number; y: number; type: string; ownerId: string }[]
}

const EMPTY_STATE: GameState = {
  botRunning: false,
  botPid: null,
  botUptime: null,
  aiRunning: false,
  aiPid: null,
  aiUptime: null,
  tick: null,
  agent: null,
  units: { workers: 0, soldiers: 0, healers: 0, total: 0 },
  structures: { spawns: 0, towers: 0, storages: 0, spawnEnergy: 0 },
  threats: { enemyUnits: 0 },
  params: {},
  llmConfig: null,
  mapChunks: [],
  humanSuggestion: null,
  chatMessages: [],
}

export function useWebSocket() {
  const [state, setState] = useState<GameState>(EMPTY_STATE)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

  const connect = useCallback(function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data)
      if (msg.type === "state") {
        setState((prev) => ({ ...prev, ...msg.data }))
      } else if (msg.type === "log_entry") {
        setLogs((prev) => [msg.data, ...prev].slice(0, 200))
      }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    // Load initial log entries
    fetch("/api/strategy/log?limit=100")
      .then((r) => r.json())
      .then((entries: LogEntry[]) => setLogs(entries.reverse()))
      .catch(() => {})

    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { state, logs, connected, send }
}
