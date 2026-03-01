"use client"

import { Box } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export function Header({ onLogoClick }: { onLogoClick?: () => void }) {
  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 border-b border-border bg-card">
      <button
        onClick={onLogoClick}
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <Box className="size-5 text-[#6366f1]" />
        <span className="text-xl font-bold text-[#6366f1] font-sans">
          RepoScout
        </span>
      </button>
      <Badge
        variant="secondary"
        className="text-muted-foreground text-xs font-normal bg-muted"
      >
        Powered by Mistral AI
      </Badge>
    </header>
  )
}
