"use client"

import { Search, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface SearchHeroProps {
  query: string
  onQueryChange: (query: string) => void
  onSearch: () => void
  isLoading: boolean
  activeMode: string
  onModeChange: (mode: string) => void
}

const modes = [
  { id: "solve", label: "How does the world solve X?" },
  { id: "compare", label: "Compare packages" },
  { id: "health", label: "Health check" },
]

export function SearchHero({
  query,
  onQueryChange,
  onSearch,
  isLoading,
  activeMode,
  onModeChange,
}: SearchHeroProps) {
  return (
    <section className="flex flex-col items-center px-6 py-12 gap-6">
      <div className="text-center flex flex-col gap-3 max-w-2xl">
        <h1 className="text-3xl font-bold text-foreground text-balance">
          The Open Source Intelligence Engine
        </h1>
        <p className="text-muted-foreground text-balance">
          Query 2.6M packages and 235M dependency relationships. Real data, not
          opinions.
        </p>
      </div>

      <div className="flex w-full max-w-2xl flex-col gap-4">
        <div className="relative flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isLoading) onSearch()
              }}
              placeholder="How do Python projects handle authentication?"
              className="h-12 pl-11 pr-4 rounded-xl shadow-md border-border bg-card text-foreground placeholder:text-muted-foreground focus-visible:ring-[#6366f1] focus-visible:border-[#6366f1] transition-all"
            />
          </div>
          <Button
            onClick={onSearch}
            disabled={isLoading || !query.trim()}
            className="h-12 px-6 rounded-xl bg-[#6366f1] text-[#ffffff] hover:bg-[#5558e6] transition-colors"
          >
            {isLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Search className="size-4" />
            )}
            <span className="ml-2">Analyze</span>
          </Button>
        </div>

        <div className="flex items-center justify-center gap-2 flex-wrap">
          {modes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => onModeChange(mode.id)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all cursor-pointer ${
                activeMode === mode.id
                  ? "bg-[#6366f1] text-[#ffffff] shadow-sm"
                  : "bg-muted text-muted-foreground hover:bg-[#e0e0e8]"
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
