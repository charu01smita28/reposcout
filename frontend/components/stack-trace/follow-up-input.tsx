"use client"

import { Send } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface FollowUpInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
}

export function FollowUpInput({ value, onChange, onSend }: FollowUpInputProps) {
  return (
    <div className="sticky bottom-0 border-t border-border bg-card/95 backdrop-blur-sm px-6 py-4">
      <div className="max-w-3xl mx-auto flex flex-col gap-2">
        <div className="flex gap-2">
          <Input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && value.trim()) onSend()
            }}
            placeholder="Ask a follow-up question..."
            className="h-10 rounded-lg border-border bg-muted text-foreground placeholder:text-muted-foreground focus-visible:ring-[#6366f1] focus-visible:border-[#6366f1]"
          />
          <Button
            onClick={onSend}
            disabled={!value.trim()}
            className="h-10 px-4 rounded-lg bg-[#6366f1] text-[#ffffff] hover:bg-[#5558e6]"
          >
            <Send className="size-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground text-center">
          Querying 2.6M packages &bull; 235M dependencies &bull; Powered by Mistral AI
        </p>
      </div>
    </div>
  )
}
