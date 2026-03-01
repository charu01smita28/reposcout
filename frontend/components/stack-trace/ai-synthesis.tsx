"use client"

import { useState } from "react"
import { Zap, ChevronDown, ChevronUp } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface DataSource {
  label: string
  url?: string
}

interface SynthesisData {
  summary: string
  recommendation: string
  dataSources: DataSource[]
  followUps: { text: string; borderColor: string }[]
}

interface AISynthesisProps {
  data: SynthesisData
  onFollowUp: (query: string) => void
}

export function AISynthesis({ data, onFollowUp }: AISynthesisProps) {
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
              {data.summary}
            </p>
            <div className="text-sm text-foreground leading-relaxed prose prose-sm max-w-none prose-headings:text-foreground prose-headings:text-sm prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1.5 prose-p:leading-relaxed prose-ul:my-1 prose-li:my-0.5 prose-hr:my-2 prose-hr:border-border/40 prose-strong:text-foreground prose-a:text-primary prose-a:no-underline hover:prose-a:underline prose-table:text-xs prose-th:bg-muted/50 prose-th:px-2 prose-th:py-1.5 prose-td:px-2 prose-td:py-1.5 prose-th:font-medium prose-th:text-left prose-td:text-foreground prose-th:text-foreground">
              <div className="overflow-x-auto">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.recommendation}</ReactMarkdown>
              </div>
            </div>
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
              <ol className="flex flex-col gap-1.5 pl-5 list-decimal">
                {data.dataSources.map((source) => (
                  <li
                    key={source.label}
                    className="text-xs text-muted-foreground"
                  >
                    {source.url ? (
                      <span>
                        {source.label}{" "}
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#6366f1] hover:underline break-all"
                        >
                          {source.url}
                        </a>
                      </span>
                    ) : (
                      source.label
                    )}
                  </li>
                ))}
              </ol>
            </CollapsibleContent>
          </Collapsible>

          {/* Follow-up suggestions */}
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Suggested follow-ups
            </p>
            <div className="flex flex-col gap-2">
              {data.followUps.map((followUp) => (
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
