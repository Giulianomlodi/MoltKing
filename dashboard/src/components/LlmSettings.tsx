import { useEffect, useState } from "react"
import { Popover as PopoverPrimitive } from "radix-ui"
import { Settings, Eye, EyeOff } from "lucide-react"
import { Button } from "@/components/ui/button"

interface LlmConfig {
  provider: string
  model: string
  keyHint: string
  hasKey: boolean
  models: Record<string, string[]>
}

interface LlmSettingsProps {
  aiRunning: boolean
}

export default function LlmSettings({ aiRunning }: LlmSettingsProps) {
  const [open, setOpen] = useState(false)
  const [config, setConfig] = useState<LlmConfig | null>(null)
  const [provider, setProvider] = useState("")
  const [model, setModel] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  // Fetch config when popover opens
  useEffect(() => {
    if (!open) return
    fetch("/api/llm/config")
      .then((r) => r.json())
      .then((cfg: LlmConfig) => {
        setConfig(cfg)
        setProvider(cfg.provider)
        setModel(cfg.model)
        setApiKey("")
        setShowKey(false)
        setDirty(false)
      })
      .catch(() => { })
  }, [open])

  const availableModels = config?.models?.[provider] ?? []

  // When provider changes, reset model to first available
  function handleProviderChange(newProvider: string) {
    setProvider(newProvider)
    const models = config?.models?.[newProvider] ?? []
    if (models.length > 0 && !models.includes(model)) {
      setModel(models[0])
    }
    setDirty(true)
  }

  async function handleSave() {
    setSaving(true)
    const body: Record<string, string> = { provider, model }
    if (apiKey) body.api_key = apiKey
    try {
      await fetch("/api/llm/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      setDirty(false)
      setOpen(false)
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
          <Settings className="h-4 w-4" />
        </Button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="end"
          sideOffset={8}
          className="z-50 w-80 rounded-lg border border-border bg-background p-4 shadow-lg"
        >
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">LLM Settings</h3>

            {aiRunning && (
              <p className="text-xs text-yellow-500">
                Changes take effect after AI restart
              </p>
            )}

            {/* Provider */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Provider</label>
              <select
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              >
                {config && Object.keys(config.models).map((p) => (
                  <option key={p} value={p}>
                    {p === "nvidia" ? "NVIDIA" : p.charAt(0).toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Model */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Model</label>
              <select
                value={model}
                onChange={(e) => { setModel(e.target.value); setDirty(true) }}
                className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              >
                {availableModels.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            {/* API Key */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">API Key</label>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => { setApiKey(e.target.value); setDirty(true) }}
                  placeholder={config?.hasKey ? `Current: ${config.keyHint}` : "Enter API key"}
                  className="w-full rounded-md border border-border bg-background px-2 py-1.5 pr-8 text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={!dirty || saving}
              >
                {saving ? "Saving..." : "Save"}
              </Button>
            </div>
          </div>
          <PopoverPrimitive.Arrow className="fill-border" />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}
