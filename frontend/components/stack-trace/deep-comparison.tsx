"use client"

import { Star, ArrowUpRight, ArrowDownRight, Package, Calendar, Download, Users, TrendingUp, GitFork, Scale, Hash, Minus } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { type PackageStats } from "@/lib/api"

const AVATAR_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

interface DeepComparisonProps {
  packages: PackageStats[]
  downloadTotals?: Record<string, number>
}

function getInitials(name: string): string {
  const parts = name.replace(/[-_]/g, " ").split(" ")
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return n.toLocaleString()
}

function relativeTime(days: number): string {
  if (days <= 1) return "Today"
  if (days <= 7) return `${days}d ago`
  if (days <= 30) return `${Math.round(days / 7)}w ago`
  if (days <= 365) return `${Math.round(days / 30)}mo ago`
  return `${(days / 365).toFixed(1)}yr ago`
}

function BestBadge() {
  return (
    <span className="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#dcfce7] text-[#15803d] border border-[#bbf7d0]">
      Best
    </span>
  )
}

function HealthBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-[#dcfce7] text-[#15803d] border-[#bbf7d0]"
      : score >= 60
        ? "bg-[#fef9c3] text-[#a16207] border-[#fde68a]"
        : "bg-[#fee2e2] text-[#dc2626] border-[#fecaca]"

  return (
    <span
      className={`inline-flex items-center justify-center size-10 rounded-full text-sm font-bold border ${color}`}
    >
      {score}
    </span>
  )
}

type Metric = {
  label: string
  icon: React.ReactNode
  render: (p: PackageStats, idx: number) => React.ReactNode
  skip?: boolean
}

type Section = {
  title: string
  icon: React.ReactNode
  metrics: Metric[]
}

export function DeepComparison({ packages, downloadTotals }: DeepComparisonProps) {
  if (packages.length < 2) return null

  const best = (fn: (p: PackageStats) => number, higher = true) =>
    packages.reduce((b, p, i) =>
      higher
        ? fn(p) > fn(packages[b]) ? i : b
        : fn(p) < fn(packages[b]) ? i : b
    , 0)

  const bestHealth = best((p) => p.reposcout_score || 0)
  const bestStars = best((p) => p.stars || 0)
  const bestDependents = best((p) => p.dependents_count || 0)
  const bestGrowth = best((p) => p.growth_pct || 0)
  const bestForks = best((p) => p.forks || 0)
  const bestVersions = best((p) => p.total_versions || 0)
  const bestRelease = best((p) => p.days_since_last_release || Infinity, false)

  const hasDownloads = downloadTotals && Object.keys(downloadTotals).length > 0
  let bestDownloads = -1
  if (hasDownloads) {
    bestDownloads = packages.reduce((b, p, i) => {
      const cur = downloadTotals[p.name] || 0
      const bv = downloadTotals[packages[b].name] || 0
      return cur > bv ? i : b
    }, 0)
  }

  const colTemplate = `160px repeat(${packages.length}, 1fr)`

  const sections: Section[] = [
    {
      title: "Health & Popularity",
      icon: <TrendingUp className="size-4" />,
      metrics: [
        {
          label: "Health Score",
          icon: <TrendingUp className="size-4 text-muted-foreground" />,
          render: (p, idx) => (
            <div className="flex items-center gap-1.5">
              <HealthBadge score={Math.round(p.reposcout_score || 0)} />
              {idx === bestHealth && <BestBadge />}
            </div>
          ),
        },
        {
          label: "GitHub Stars",
          icon: <Star className="size-4 text-muted-foreground" />,
          render: (p, idx) => (
            <div className="flex items-center gap-1.5">
              <Star className="size-3.5 text-amber-400 fill-amber-400" />
              <span className="font-medium text-sm">{formatNumber(p.stars || 0)}</span>
              {idx === bestStars && <BestBadge />}
            </div>
          ),
        },
        {
          label: "Dependents",
          icon: <Users className="size-4 text-muted-foreground" />,
          render: (p, idx) => (
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-sm">{formatNumber(p.dependents_count || 0)}</span>
              {idx === bestDependents && <BestBadge />}
            </div>
          ),
        },
        {
          label: "Monthly Downloads",
          icon: <Download className="size-4 text-muted-foreground" />,
          skip: !hasDownloads,
          render: (p, idx) => {
            const val = downloadTotals?.[p.name] || 0
            if (val === 0) return <span className="text-sm text-muted-foreground">—</span>
            return (
              <div className="flex items-center gap-1.5">
                <Download className="size-3.5 text-muted-foreground" />
                <span className="font-medium text-sm">{formatNumber(val)}</span>
                {idx === bestDownloads && <BestBadge />}
              </div>
            )
          },
        },
        {
          label: "YoY Growth",
          icon: <ArrowUpRight className="size-4 text-muted-foreground" />,
          render: (p, idx) => {
            const g = p.growth_pct || 0
            const color = g > 5 ? "text-emerald-600" : g < -5 ? "text-red-500" : "text-muted-foreground"
            const Icon = g > 0 ? ArrowUpRight : g < 0 ? ArrowDownRight : Minus
            return (
              <div className="flex items-center gap-1">
                <Icon className={`size-3.5 ${color}`} />
                <span className={`font-medium text-sm ${color}`}>{g.toFixed(1)}%</span>
                {idx === bestGrowth && <BestBadge />}
              </div>
            )
          },
        },
      ],
    },
    {
      title: "Maintenance & Maturity",
      icon: <Calendar className="size-4" />,
      metrics: [
        {
          label: "Latest Release",
          icon: <Calendar className="size-4 text-muted-foreground" />,
          render: (p, idx) => {
            const days = p.days_since_last_release
            const color = days <= 90 ? "text-emerald-600" : days <= 365 ? "text-amber-600" : "text-red-500"
            return (
              <div className="flex items-center gap-1.5">
                <span className={`text-sm font-medium ${color}`}>
                  {p.latest_version || "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  ({relativeTime(days)})
                </span>
                {idx === bestRelease && <BestBadge />}
              </div>
            )
          },
        },
        {
          label: "Total Versions",
          icon: <Hash className="size-4 text-muted-foreground" />,
          render: (p, idx) => (
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-sm">{p.total_versions || 0} releases</span>
              {idx === bestVersions && <BestBadge />}
            </div>
          ),
        },
        {
          label: "Forks",
          icon: <GitFork className="size-4 text-muted-foreground" />,
          render: (p, idx) => (
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-sm">{formatNumber(p.forks || 0)}</span>
              {idx === bestForks && <BestBadge />}
            </div>
          ),
        },
        {
          label: "License",
          icon: <Scale className="size-4 text-muted-foreground" />,
          render: (p) => (
            <span className="text-sm font-medium">{p.license || "—"}</span>
          ),
        },
      ],
    },
  ]

  return (
    <section className="px-6 pb-6">
      <div className="max-w-5xl mx-auto">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <CardTitle className="text-base">Framework Deep Comparison</CardTitle>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                {packages.length} packages
              </span>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {/* Avatar row — centered in columns */}
            <div
              className="grid gap-4 px-4 mb-6"
              style={{ gridTemplateColumns: colTemplate }}
            >
              <div />
              {packages.map((p, i) => (
                <div key={p.name} className="flex flex-col items-center text-center gap-1.5">
                  <div
                    className="size-12 rounded-full flex items-center justify-center text-white text-sm font-bold"
                    style={{ backgroundColor: AVATAR_COLORS[i % AVATAR_COLORS.length] }}
                  >
                    {getInitials(p.name)}
                  </div>
                  <div className="font-semibold text-sm">{p.name}</div>
                  <div className="text-xs text-muted-foreground line-clamp-1 max-w-[200px]">
                    {p.summary || ""}
                  </div>
                </div>
              ))}
            </div>

            {/* Sectioned comparison rows */}
            <div className="border rounded-lg overflow-hidden">
              {sections.map((section) => {
                const visibleMetrics = section.metrics.filter((m) => !m.skip)
                if (visibleMetrics.length === 0) return null
                return (
                  <div key={section.title}>
                    {/* Section header */}
                    <div className="flex items-center gap-2 px-4 py-2.5 bg-muted/60 border-b">
                      {section.icon}
                      <span className="text-sm font-semibold">{section.title}</span>
                    </div>
                    {/* Metric rows */}
                    {visibleMetrics.map((metric, mIdx) => (
                      <div
                        key={metric.label}
                        className={`grid items-center gap-4 px-4 py-3 ${mIdx % 2 === 0 ? "" : "bg-muted/20"}`}
                        style={{ gridTemplateColumns: colTemplate }}
                      >
                        <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
                          {metric.icon}
                          {metric.label}
                        </div>
                        {packages.map((p, idx) => (
                          <div key={p.name} className="flex justify-center">{metric.render(p, idx)}</div>
                        ))}
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
