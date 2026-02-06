import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import type { MapChunk } from "@/hooks/useWebSocket"

interface LiveMapProps {
  chunks: MapChunk[]
  myAgentId: string | null
}

const CELL = 4
const CHUNK_SIZE = 25

const TERRAIN_COLORS: Record<string, string> = {
  wall: "#1a1a2e",
  swamp: "#2d4a3e",
  plain: "#2a2a3a",
}

export default function LiveMap({ chunks, myAgentId }: LiveMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [showTerrain, setShowTerrain] = useState(true)

  useEffect(() => {
    if (collapsed || !canvasRef.current || chunks.length === 0) return
    const ctx = canvasRef.current.getContext("2d")
    if (!ctx) return

    // Find bounds
    let minCx = Infinity, minCy = Infinity, maxCx = -Infinity, maxCy = -Infinity
    for (const c of chunks) {
      minCx = Math.min(minCx, c.x)
      minCy = Math.min(minCy, c.y)
      maxCx = Math.max(maxCx, c.x)
      maxCy = Math.max(maxCy, c.y)
    }

    const cols = maxCx - minCx + 1
    const rows = maxCy - minCy + 1
    const w = cols * CHUNK_SIZE * CELL
    const h = rows * CHUNK_SIZE * CELL
    canvasRef.current.width = w
    canvasRef.current.height = h

    ctx.fillStyle = "#111"
    ctx.fillRect(0, 0, w, h)

    for (const chunk of chunks) {
      const ox = (chunk.x - minCx) * CHUNK_SIZE * CELL
      const oy = (chunk.y - minCy) * CHUNK_SIZE * CELL

      // Terrain
      if (showTerrain && chunk.terrain) {
        for (let row = 0; row < chunk.terrain.length; row++) {
          for (let col = 0; col < (chunk.terrain[row]?.length ?? 0); col++) {
            const t = chunk.terrain[row][col]
            ctx.fillStyle = TERRAIN_COLORS[t] || TERRAIN_COLORS.plain
            ctx.fillRect(ox + col * CELL, oy + row * CELL, CELL, CELL)
          }
        }
      }

      // Sources
      for (const s of chunk.sources || []) {
        const sx = ox + (s.x % CHUNK_SIZE) * CELL
        const sy = oy + (s.y % CHUNK_SIZE) * CELL
        ctx.fillStyle = s.energy > 0 ? "#fbbf24" : "#4a4520"
        ctx.fillRect(sx, sy, CELL, CELL)
      }

      // Structures
      for (const s of chunk.structures || []) {
        const sx = ox + (s.x % CHUNK_SIZE) * CELL
        const sy = oy + (s.y % CHUNK_SIZE) * CELL
        const mine = s.ownerId === myAgentId
        if (s.type === "spawn") ctx.fillStyle = mine ? "#3b82f6" : "#9333ea"
        else if (s.type === "tower") ctx.fillStyle = mine ? "#06b6d4" : "#dc2626"
        else if (s.type === "storage") ctx.fillStyle = mine ? "#8b5cf6" : "#be185d"
        else ctx.fillStyle = mine ? "#6b7280" : "#4b5563"
        ctx.fillRect(sx - 1, sy - 1, CELL + 2, CELL + 2)
      }

      // Units
      for (const u of chunk.units || []) {
        const ux = ox + (u.x % CHUNK_SIZE) * CELL
        const uy = oy + (u.y % CHUNK_SIZE) * CELL
        const mine = u.ownerId === myAgentId
        if (u.type === "worker") ctx.fillStyle = mine ? "#10b981" : "#f97316"
        else if (u.type === "soldier") ctx.fillStyle = mine ? "#ef4444" : "#f43f5e"
        else ctx.fillStyle = mine ? "#a78bfa" : "#fb923c"
        ctx.beginPath()
        ctx.arc(ux + CELL / 2, uy + CELL / 2, CELL / 2, 0, Math.PI * 2)
        ctx.fill()
      }
    }
  }, [chunks, collapsed, showTerrain, myAgentId])

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          Live Map
          <div className="flex gap-2">
            {!collapsed && (
              <Button size="sm" variant="ghost" onClick={() => setShowTerrain(!showTerrain)} className="text-xs">
                {showTerrain ? "Hide Terrain" : "Show Terrain"}
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={() => setCollapsed(!collapsed)} className="text-xs">
              {collapsed ? "Expand" : "Collapse"}
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      {!collapsed && (
        <CardContent className="overflow-auto p-2">
          {chunks.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No map data available. Start the bot to see the map.
            </p>
          ) : (
            <canvas ref={canvasRef} className="mx-auto rounded" />
          )}
          <div className="mt-2 flex flex-wrap justify-center gap-3 text-xs text-muted-foreground">
            <span><span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> My workers</span>
            <span><span className="inline-block h-2 w-2 rounded-full bg-red-500" /> My soldiers</span>
            <span><span className="inline-block h-2 w-2 rounded bg-blue-500" /> My spawns</span>
            <span><span className="inline-block h-2 w-2 rounded bg-cyan-500" /> My towers</span>
            <span><span className="inline-block h-2 w-2 rounded bg-yellow-400" /> Sources</span>
            <span><span className="inline-block h-2 w-2 rounded-full bg-orange-500" /> Enemy units</span>
          </div>
        </CardContent>
      )}
    </Card>
  )
}
