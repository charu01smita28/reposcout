"use client"

import { Box } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
      <div className="flex items-center gap-2">
        <Box className="size-5 text-[#6366f1]" />
        <span className="text-xl font-bold text-[#6366f1] font-sans">
          RepoScout
        </span>
      </div>
      <Badge
        variant="secondary"
        className="text-muted-foreground text-xs font-normal bg-muted"
      >
        Powered by Mistral AI
      </Badge>
    </header>
  )
}
