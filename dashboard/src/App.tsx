import { useWebSocket } from "@/hooks/useWebSocket"
import Header from "@/components/Header"
import GameOverview from "@/components/GameOverview"
import AITimeline from "@/components/AITimeline"
import StrategyEvolution from "@/components/StrategyEvolution"
import GameChat from "@/components/GameChat"
import HumanSuggestion from "@/components/HumanSuggestion"

function App() {
  const { state, logs, connected, send } = useWebSocket()

  return (
    <div className="min-h-screen bg-background">
      <Header state={state} connected={connected} send={send} />
      <main className="mx-auto max-w-7xl space-y-4 p-4">
        <GameOverview state={state} />
        <HumanSuggestion state={state} send={send} />
        <div className="grid gap-4 lg:grid-cols-2">
          <AITimeline logs={logs} />
          <StrategyEvolution logs={logs} />
        </div>
        <GameChat messages={state.chatMessages} myName={state.agent?.name ?? "MoltKing"} />
      </main>
    </div>
  )
}

export default App
