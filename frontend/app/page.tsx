"use client"

import { useState, useRef, useCallback } from "react"
import { Header } from "@/components/stack-trace/header"
import { SearchHero } from "@/components/stack-trace/search-hero"
import { SuggestionCards } from "@/components/stack-trace/suggestion-cards"
import { StatsBanner } from "@/components/stack-trace/stats-banner"
import { ComparisonTable } from "@/components/stack-trace/comparison-table"
import { ChartsSection } from "@/components/stack-trace/charts-section"
import { DependencyMap } from "@/components/stack-trace/dependency-map"
import { PackageDeepDive } from "@/components/stack-trace/package-deep-dive"
import { AISynthesis } from "@/components/stack-trace/ai-synthesis"
import { LoadingPipeline } from "@/components/stack-trace/loading-states"
import { FollowUpInput } from "@/components/stack-trace/follow-up-input"
import { DeepComparison } from "@/components/stack-trace/deep-comparison"
import {
  searchAgent,
  getDownloadTrends,
  type SearchResponse,
  type PackageStats,
  type DownloadDataPoint,
} from "@/lib/api"
import { type PackageData } from "@/lib/sample-data"

type AppState = "idle" | "loading" | "results" | "error"

export default function RepoScoutPage() {
  const [query, setQuery] = useState("")
  const [followUpQuery, setFollowUpQuery] = useState("")
  const [activeMode, setActiveMode] = useState("auto")
  const [appState, setAppState] = useState<AppState>("idle")
  const [errorMsg, setErrorMsg] = useState("")
  const resultsRef = useRef<HTMLDivElement>(null)

  // Real data from API
  const [analysisText, setAnalysisText] = useState("")
  const [toolCalls, setToolCalls] = useState<SearchResponse["tool_calls"]>([])
  const [detectedMode, setDetectedMode] = useState("")
  const [iterations, setIterations] = useState(0)
  const [packageStats, setPackageStats] = useState<PackageStats[]>([])
  const [searchResults, setSearchResults] = useState<Record<string, unknown> | null>(null)
  const [selectedPackage, setSelectedPackage] = useState<string | null>(null)
  const [lineChartData, setLineChartData] = useState<Record<string, string | number>[]>([])
  const [lineChartPackages, setLineChartPackages] = useState<string[]>([])

  const fetchDownloadTrends = (pkgNames: string[]) => {
    const names = pkgNames.slice(0, 5)
    if (names.length === 0) return
    getDownloadTrends(names)
      .then((data) => {
        if (!data || data.length === 0) return
        // Pivot flat data → recharts wide format: [{ month, pkg1: n, pkg2: n }, ...]
        const months = [...new Set(data.map((d) => d.month))].sort()
        const pivoted = months.map((m) => {
          const row: Record<string, string | number> = { month: m }
          for (const name of names) {
            const point = data.find((d) => d.month === m && d.package_name === name)
            if (point) row[name] = point.downloads
          }
          return row
        })
        setLineChartData(pivoted)
        setLineChartPackages(names)
      })
      .catch(() => {})
  }

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setAppState("loading")
    setErrorMsg("")
    setLineChartData([])
    setLineChartPackages([])

    try {
      const result = await searchAgent(query, activeMode)
      setAnalysisText(result.analysis)
      setToolCalls(result.tool_calls)
      setDetectedMode(result.mode)
      setIterations(result.iterations)

      // Use structured data from backend
      setPackageStats(result.packages || [])
      setSearchResults(result.search)

      // Select first package by default
      const pkgs = result.packages || []
      if (pkgs.length > 0) {
        setSelectedPackage(pkgs[0].name)
      }

      setAppState("results")
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth" })
      }, 100)

      // Non-blocking: fetch download trends in background
      fetchDownloadTrends(pkgs.map((p) => p.name))
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong")
      setAppState("error")
    }
  }, [query, activeMode])

  const handleSuggestionSelect = (suggestion: string) => {
    setQuery(suggestion)
    setLineChartData([])
    setLineChartPackages([])
    // Trigger search after state update
    setTimeout(async () => {
      setAppState("loading")
      try {
        const result = await searchAgent(suggestion, activeMode)
        setAnalysisText(result.analysis)
        setToolCalls(result.tool_calls)
        setDetectedMode(result.mode)
        setIterations(result.iterations)
        setPackageStats(result.packages || [])
        setSearchResults(result.search)
        const pkgs = result.packages || []
        if (pkgs.length > 0) {
          setSelectedPackage(pkgs[0].name)
        }
        setAppState("results")
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: "smooth" })
        }, 100)
        fetchDownloadTrends(pkgs.map((p) => p.name))
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Something went wrong")
        setAppState("error")
      }
    }, 200)
  }

  const handleFollowUp = (text: string) => {
    setQuery(text)
    setFollowUpQuery("")
    setTimeout(() => handleSearch(), 100)
  }

  const handleSelectPackageFromTable = (pkg: PackageData) => {
    setSelectedPackage(pkg.name)
  }

  const handleSelectPackageFromMap = (name: string) => {
    setSelectedPackage(name)
  }

  // Transform PackageStats[] into the shape ComparisonTable expects
  const tableData: PackageData[] = packageStats.map((p) => ({
    name: p.name,
    dependents: p.dependents_count || 0,
    stars: p.stars || 0,
    health: Math.round(p.reposcout_score || 0),
    lastRelease:
      p.days_since_last_release <= 7
        ? "This week"
        : p.days_since_last_release <= 30
          ? `${Math.round(p.days_since_last_release / 7)} weeks ago`
          : p.days_since_last_release <= 365
            ? `${Math.round(p.days_since_last_release / 30)} months ago`
            : `${Math.round(p.days_since_last_release / 365)} years ago`,
    lastReleaseStatus:
      p.days_since_last_release <= 90
        ? "green"
        : p.days_since_last_release <= 365
          ? "amber"
          : "red",
    trend: p.growth_pct || 0,
    trendDirection:
      (p.growth_pct || 0) > 5
        ? "up"
        : (p.growth_pct || 0) < -5
          ? "down"
          : "neutral",
    summary: p.summary || "",
  }))

  // Bar chart data
  const barData = tableData
    .map((p) => ({ name: p.name, dependents: p.dependents }))
    .sort((a, b) => b.dependents - a.dependents)

  // Download totals for deep comparison (latest month per package)
  const downloadTotals: Record<string, number> = {}
  if (lineChartData.length > 0 && lineChartPackages.length > 0) {
    const lastRow = lineChartData[lineChartData.length - 1]
    for (const name of lineChartPackages) {
      const val = lastRow[name]
      if (typeof val === "number" && val > 0) downloadTotals[name] = val
    }
  }

  // Stats banner data
  const statCards = packageStats.length > 0
    ? [
        {
          label: "Packages Analyzed",
          value: packageStats.length,
          type: "number" as const,
        },
        {
          label: "Total Dependents",
          value: packageStats.reduce((sum, p) => sum + (p.dependents_count || 0), 0),
          type: "number" as const,
        },
        {
          label: "Most Popular",
          value: [...packageStats].sort((a, b) => (b.stars || 0) - (a.stars || 0))[0]?.name || "",
          sub: `${([...packageStats].sort((a, b) => (b.stars || 0) - (a.stars || 0))[0]?.stars || 0).toLocaleString()} stars`,
          type: "text" as const,
        },
        {
          label: "Most Depended On",
          value: [...packageStats].sort((a, b) => (b.dependents_count || 0) - (a.dependents_count || 0))[0]?.name || "",
          sub: `${([...packageStats].sort((a, b) => (b.dependents_count || 0) - (a.dependents_count || 0))[0]?.dependents_count || 0).toLocaleString()} dependents`,
          type: "text" as const,
        },
        {
          label: "Fastest Growing",
          value: [...packageStats].sort((a, b) => (b.growth_pct || 0) - (a.growth_pct || 0))[0]?.name || "",
          sub: `${[...packageStats].sort((a, b) => (b.growth_pct || 0) - (a.growth_pct || 0))[0]?.growth_pct || 0}% YoY`,
          type: "growth" as const,
        },
      ]
    : []

  // Dependency map data
  const depMapData = packageStats.length > 0
    ? {
        name: query,
        children: packageStats.slice(0, 6).map((p) => ({
          name: p.name,
          dependents: p.dependents_count || 0,
          health: Math.round(p.reposcout_score || 0),
          dependencies: [] as string[],
          usedBy: `${(p.dependents_count || 0).toLocaleString()} dependents`,
        })),
      }
    : null

  // Package deep dive — selected package
  const selectedPkg = packageStats.find((p) => p.name === selectedPackage)
  const deepDiveData = selectedPkg
    ? {
        name: selectedPkg.name,
        version: selectedPkg.latest_version || "",
        description: selectedPkg.summary || "",
        health: Math.round(selectedPkg.reposcout_score || 0),
        metrics: [
          {
            label: "Total Versions",
            value: `${selectedPkg.total_versions || 0} releases`,
            icon: "Calendar" as const,
            status: (selectedPkg.total_versions || 0) > 10 ? "green" as const : (selectedPkg.total_versions || 0) > 3 ? "amber" as const : "red" as const,
          },
          {
            label: "Last Release",
            value: selectedPkg.days_since_last_release <= 30
              ? "Recent"
              : selectedPkg.days_since_last_release <= 180
                ? `${Math.round(selectedPkg.days_since_last_release / 30)}mo ago`
                : `${Math.round(selectedPkg.days_since_last_release / 365)}yr ago`,
            icon: "GitBranch" as const,
            status: selectedPkg.days_since_last_release <= 90 ? "green" as const : selectedPkg.days_since_last_release <= 365 ? "amber" as const : "red" as const,
          },
          {
            label: "Stars",
            value: (selectedPkg.stars || 0).toLocaleString(),
            icon: "Users" as const,
            status: (selectedPkg.stars || 0) > 1000 ? "green" as const : (selectedPkg.stars || 0) > 100 ? "amber" as const : "red" as const,
          },
          {
            label: "Dependents",
            value: (selectedPkg.dependents_count || 0).toLocaleString(),
            icon: "MessageCircle" as const,
            status: (selectedPkg.dependents_count || 0) > 100 ? "green" as const : (selectedPkg.dependents_count || 0) > 10 ? "amber" as const : "red" as const,
          },
        ],
        codeSnippet: `pip install ${selectedPkg.name}`,
        codeSource: `PyPI: ${selectedPkg.name} v${selectedPkg.latest_version || ""}`,
      }
    : null

  // AI Synthesis data
  const synthesisData = analysisText
    ? {
        summary: `Agent ran ${iterations} iteration(s) with ${toolCalls.length} tool call(s) in ${detectedMode} mode.`,
        recommendation: analysisText,
        dataSources: [
          // Static infra sources
          ...(toolCalls.some((t) => t.tool === "search_packages")
            ? [{ label: "Qdrant Cloud — semantic search (80K vectors, Mistral Embed)" }]
            : []),
          ...(toolCalls.some((t) => t.tool === "get_package_stats" || t.tool === "compare_packages")
            ? [{ label: "DuckDB — 85K+ packages (stars, dependents, growth trends)" }]
            : []),
          // Per-package links: PyPI + GitHub
          ...packageStats.flatMap((p) => {
            const ghUrl = p.repository_url
              ? (p.repository_url.startsWith("http") ? p.repository_url : `https://github.com/${p.repository_url}`)
              : ""
            return [
              { label: `PyPI: ${p.name}`, url: `https://pypi.org/project/${p.name}/` },
              ...(ghUrl ? [{ label: `GitHub: ${p.name}`, url: ghUrl }] : []),
            ]
          }),
        ],
        followUps: [
          { text: `Compare the top 3 packages from this search`, borderColor: "border-l-[#6366f1]" },
          { text: `Which of these packages is safest to depend on?`, borderColor: "border-l-[#10b981]" },
          { text: `Show me implementation patterns for ${selectedPackage || "the top package"}`, borderColor: "border-l-[#f59e0b]" },
        ],
      }
    : null

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      <main className="flex-1 flex flex-col">
        <SearchHero
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          isLoading={appState === "loading"}
          activeMode={activeMode}
          onModeChange={setActiveMode}
        />

        {appState === "idle" && (
          <SuggestionCards onSelect={handleSuggestionSelect} activeMode={activeMode} />
        )}

        {appState === "loading" && <LoadingPipeline />}

        {appState === "error" && (
          <div className="px-6 pb-6 max-w-5xl mx-auto">
            <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {errorMsg || "Something went wrong. Is the backend running on port 8000?"}
            </div>
          </div>
        )}

        {appState === "results" && (
          <div ref={resultsRef} className="flex flex-col">
            {statCards.length > 0 && <StatsBanner stats={statCards} />}
            {tableData.length > 0 && (
              detectedMode === "compare" && packageStats.length >= 2 ? (
                <DeepComparison
                  packages={packageStats}
                  downloadTotals={Object.keys(downloadTotals).length > 0 ? downloadTotals : undefined}
                />
              ) : (
                <ComparisonTable
                  data={tableData}
                  onSelectPackage={handleSelectPackageFromTable}
                  selectedPackage={selectedPackage}
                />
              )
            )}
            {barData.length > 0 && (
              <ChartsSection
                barData={barData}
                lineData={lineChartData.length > 0 ? lineChartData : undefined}
                packageNames={lineChartPackages.length > 0 ? lineChartPackages : undefined}
              />
            )}
            {depMapData && (
              <DependencyMap
                data={depMapData}
                onSelectPackage={handleSelectPackageFromMap}
                selectedPackage={selectedPackage}
              />
            )}
            {deepDiveData && <PackageDeepDive data={deepDiveData} />}
            {synthesisData && (
              <AISynthesis data={synthesisData} onFollowUp={handleFollowUp} />
            )}
          </div>
        )}
      </main>

      {appState === "results" && (
        <FollowUpInput
          value={followUpQuery}
          onChange={setFollowUpQuery}
          onSend={() => handleFollowUp(followUpQuery)}
        />
      )}
    </div>
  )
}
