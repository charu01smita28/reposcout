"use client"

import { useEffect, useState } from "react"
import { ArrowUpRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { statCards } from "@/lib/sample-data"

function AnimatedNumber({ target }: { target: number }) {
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    const duration = 1200
    const steps = 40
    const increment = target / steps
    let step = 0

    const timer = setInterval(() => {
      step++
      if (step >= steps) {
        setCurrent(target)
        clearInterval(timer)
      } else {
        setCurrent(Math.floor(increment * step))
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [target])

  return (
    <span>{current >= 1000 ? current.toLocaleString() : current}</span>
  )
}

export function StatsBanner() {
  return (
    <section className="px-6 pb-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl mx-auto">
        {statCards.map((stat) => (
          <Card
            key={stat.label}
            className={`py-4 shadow-sm ${stat.type === "growth" ? "bg-[#ecfdf5]" : "bg-card"}`}
          >
            <CardContent className="flex flex-col gap-1">
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              {stat.type === "number" ? (
                <p className="text-2xl font-bold text-foreground">
                  <AnimatedNumber target={stat.value as number} />
                </p>
              ) : stat.type === "growth" ? (
                <div>
                  <p className="text-2xl font-bold font-mono text-foreground">
                    {stat.value}
                  </p>
                  <div className="flex items-center gap-1 text-[#10b981]">
                    <ArrowUpRight className="size-3" />
                    <span className="text-xs font-medium">{stat.sub}</span>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-2xl font-bold font-mono text-foreground">
                    {stat.value}
                  </p>
                  <p className="text-xs text-muted-foreground">{stat.sub}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
