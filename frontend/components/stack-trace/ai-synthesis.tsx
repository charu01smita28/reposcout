"use client"

import { useState } from "react"
import { Zap, ChevronDown, ChevronUp } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { aiSynthesis } from "@/lib/sample-data"

interface AISynthesisProps {
  onFollowUp: (query: string) => void
}

export function AISynthesis({ onFollowUp }: AISynthesisProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false)

  return (
    <section className="px-6 pb-6">
      <Card className="shadow-sm max-w-5xl mx-auto py-0">
        <CardHeader className="pb-0 pt-5">
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap className="size-4 text-[#6366f1]" />
            AI Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 pb-5 flex flex-col gap-5">
          {/* Summary */}
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground leading-relaxed">
              {aiSynthesis.summary}
            </p>
            <p
              className="text-sm text-foreground leading-relaxed"
              dangerouslySetInnerHTML={{
                __html: aiSynthesis.recommendation
                  .replace(
                    /\*\*(.*?)\*\*/g,
                    '<strong class="text-foreground font-semibold">$1</strong>'
                  ),
              }}
            />
          </div>

          {/* Data Sources */}
          <Collapsible open={sourcesOpen} onOpenChange={setSourcesOpen}>
            <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
              {sourcesOpen ? (
                <ChevronUp className="size-3.5" />
              ) : (
                <ChevronDown className="size-3.5" />
              )}
              Data Sources
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-2">
              <ul className="flex flex-col gap-1.5 pl-5 list-disc">
                {aiSynthesis.dataSources.map((source) => (
                  <li
                    key={source}
                    className="text-xs text-muted-foreground"
                  >
                    {source}
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>

          {/* Follow-up suggestions */}
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Suggested follow-ups
            </p>
            <div className="flex flex-col gap-2">
              {aiSynthesis.followUps.map((followUp) => (
                <button
                  key={followUp.text}
                  onClick={() => onFollowUp(followUp.text)}
                  className={`text-left border-l-[3px] ${followUp.borderColor} pl-3 py-2 px-3 rounded-r-lg text-sm text-foreground bg-muted/40 hover:bg-muted hover:-translate-y-0.5 hover:shadow-sm transition-all cursor-pointer`}
                >
                  {followUp.text}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
