"use client"

import { useState } from "react"
import {
  Users,
  Calendar,
  MessageCircle,
  GitBranch,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { packageDeepDive } from "@/lib/sample-data"

const iconMap = {
  Users,
  Calendar,
  MessageCircle,
  GitBranch,
}

function HealthRing({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 36
  const offset = circumference - (score / 100) * circumference
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444"

  return (
    <div className="relative flex items-center justify-center">
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle
          cx="40"
          cy="40"
          r="36"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="6"
        />
        <circle
          cx="40"
          cy="40"
          r="36"
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 40 40)"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <span className="absolute text-lg font-bold text-foreground">
        {score}
      </span>
    </div>
  )
}

function StatusDot({ status }: { status: "green" | "amber" | "red" }) {
  const color =
    status === "green"
      ? "bg-[#10b981]"
      : status === "amber"
        ? "bg-[#f59e0b]"
        : "bg-[#ef4444]"
  return <span className={`inline-block size-2 rounded-full ${color}`} />
}

export function PackageDeepDive() {
  const [copied, setCopied] = useState(false)
  const pkg = packageDeepDive

  const handleCopy = () => {
    navigator.clipboard.writeText(pkg.codeSnippet)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section className="px-6 pb-6">
      <Card className="shadow-sm max-w-5xl mx-auto py-0">
        <CardHeader className="pb-0 pt-5">
          <CardTitle className="text-base">Package Deep Dive</CardTitle>
        </CardHeader>
        <CardContent className="pt-4 pb-5 flex flex-col gap-6">
          {/* Package header */}
          <div className="flex flex-col sm:flex-row items-start gap-6">
            <HealthRing score={pkg.health} />
            <div className="flex flex-col gap-2 flex-1">
              <div className="flex items-center gap-3 flex-wrap">
                <h3 className="text-xl font-bold font-mono text-[#6366f1]">
                  {pkg.name}
                </h3>
                <Badge
                  variant="secondary"
                  className="font-mono text-xs bg-muted text-muted-foreground"
                >
                  v{pkg.version}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {pkg.description}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="w-fit text-[#6366f1] border-[#6366f1]/30 hover:bg-[#eef2ff] hover:text-[#6366f1]"
                asChild
              >
                <a
                  href="https://github.com/laurentS/slowapi"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="size-3.5" />
                  View Source Code
                </a>
              </Button>
            </div>
          </div>

          {/* Health breakdown metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {pkg.metrics.map((metric) => {
              const Icon = iconMap[metric.icon]
              return (
                <div
                  key={metric.label}
                  className="flex items-center gap-3 p-3 rounded-lg bg-muted/50"
                >
                  <Icon className="size-4 text-muted-foreground shrink-0" />
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs text-muted-foreground">
                      {metric.label}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <StatusDot status={metric.status} />
                      <span className="text-sm font-medium text-foreground">
                        {metric.value}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Code snippet */}
          <div className="rounded-xl overflow-hidden border border-border">
            <div className="flex items-center justify-between bg-[#1e1e2e] px-4 py-2">
              <span className="text-xs text-[#a0a0b8] font-medium">
                Implementation Pattern — Rate Limiter Setup
              </span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 text-xs text-[#a0a0b8] hover:text-[#e0e0e8] transition-colors cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="size-3" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="size-3" />
                    Copy
                  </>
                )}
              </button>
            </div>
            <pre className="bg-[#1e1e2e] px-4 py-4 overflow-x-auto">
              <code className="text-[13px] leading-relaxed font-mono text-[#e0def4]">
                {pkg.codeSnippet}
              </code>
            </pre>
            <div className="bg-[#1e1e2e] border-t border-[#2a2a3e] px-4 py-2">
              <span className="text-xs text-[#64648b]">{pkg.codeSource}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
