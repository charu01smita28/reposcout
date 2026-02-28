"use client"

import {
  Search,
  GitCompare,
  Shield,
  TrendingUp,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { suggestedQueries } from "@/lib/sample-data"

const iconMap = {
  Search,
  GitCompare,
  Shield,
  TrendingUp,
}

interface SuggestionCardsProps {
  onSelect: (query: string) => void
}

export function SuggestionCards({ onSelect }: SuggestionCardsProps) {
  return (
    <section className="px-6 pb-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl mx-auto">
        {suggestedQueries.map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <Card
              key={item.query}
              onClick={() => onSelect(item.query)}
              className={`cursor-pointer border-l-[3px] ${item.borderColor} py-4 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200`}
            >
              <CardContent className="flex flex-col gap-2">
                <Icon className="size-4 text-muted-foreground" />
                <p className="text-sm text-foreground leading-relaxed">
                  {item.query}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
