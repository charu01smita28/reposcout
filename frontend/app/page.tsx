"use client"

import { useState, useRef, useCallback } from "react"
import { Check, Loader2 } from "lucide-react"
import { Header } from "@/components/stack-trace/header"
import { SearchHero } from "@/components/stack-trace/search-hero"
import { SuggestionCards } from "@/components/stack-trace/suggestion-cards"
import { StatsBanner } from "@/components/stack-trace/stats-banner"
import { ComparisonTable } from "@/components/stack-trace/comparison-table"
import { ChartsSection } from "@/components/stack-trace/charts-section"
import { DependencyMap } from "@/components/stack-trace/dependency-map"
import { PackageDeepDive } from "@/components/stack-trace/package-deep-dive"
import { AISynthesis } from "@/components/stack-trace/ai-synthesis"
import { FollowUpInput } from "@/components/stack-trace/follow-up-input"
import { DeepComparison } from "@/components/stack-trace/deep-comparison"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  searchAgentStream,
  type SearchResponse,
  type PackageStats,
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
  const [loadingSteps, setLoadingSteps] = useState<string[]>([])
  const streamControllerRef = useRef<AbortController | null>(null)

  const startStreamingSearch = useCallback((searchQuery: string, searchMode: string) => {
    // Abort any in-flight stream
    streamControllerRef.current?.abort()

    setAppState("loading")
    setErrorMsg("")
    setAnalysisText("")
    setLineChartData([])
    setLineChartPackages([])
    setLoadingSteps([])

    const controller = searchAgentStream(
      searchQuery,
      searchMode,
      // onMetadata — cards render immediately
      (data) => {
        setToolCalls(data.tool_calls)
        setDetectedMode(data.mode)
        setIterations(data.iterations)
        setPackageStats(data.packages || [])
        setSearchResults(data.search)

        const pkgs = data.packages || []
        if (pkgs.length > 0) {
          setSelectedPackage(pkgs[0].name)
        }

        setAppState("results")
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: "smooth" })
        }, 100)
      },
      // onToken — analysis text streams in progressively
      (token) => {
        setAnalysisText((prev) => prev + token)
      },
      // onDone
      () => {},
      // onError
      (err) => {
        setErrorMsg(err.message || "Something went wrong")
        setAppState("error")
      },
      // onProgress — real-time loading hints
      (step) => {
        setLoadingSteps((prev) => [...prev, step])
      },
      // onDownloads — arrives via SSE, no separate HTTP call
      (data) => {
        if (!data || data.length === 0) return
        const names = [...new Set(data.map((d: { package_name: string }) => d.package_name))]
        const months = [...new Set(data.map((d: { month: string }) => d.month))].sort()
        const pivoted = months.map((m) => {
          const row: Record<string, string | number> = { month: m }
          for (const name of names) {
            const point = data.find((d: { month: string; package_name: string; downloads: number }) => d.month === m && d.package_name === name)
            if (point) row[name] = point.downloads
          }
          return row
        })
        setLineChartData(pivoted)
        setLineChartPackages(names)
      },
    )

    streamControllerRef.current = controller
  }, [])

  const handleSearch = useCallback(() => {
    if (!query.trim()) return
    startStreamingSearch(query, activeMode)
  }, [query, activeMode, startStreamingSearch])

  const handleSuggestionSelect = (suggestion: string) => {
    setQuery(suggestion)
    startStreamingSearch(suggestion, activeMode)
  }

  const handleFollowUp = (text: string) => {
    setQuery(text)
    setFollowUpQuery("")
    startStreamingSearch(text, activeMode)
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
        codeSnippet: selectedPkg.code_snippet || `pip install ${selectedPkg.name}`,
        codeSource: selectedPkg.code_snippet
          ? (selectedPkg.code_source || "README")
          : `PyPI: ${selectedPkg.name} v${selectedPkg.latest_version || ""}`,
      }
    : null

  // AI Synthesis data
  const synthesisData = analysisText
    ? {
        summary: `Agent ran ${iterations} iteration(s) with ${toolCalls.length} tool call(s) in ${detectedMode} mode.`,
        recommendation: analysisText,
        dataSources: [
          // Static infra sources — always shown
          { label: "Qdrant Cloud — semantic search (80K vectors, Mistral Embed)" },
          { label: "DuckDB — 85K+ packages (stars, dependents, growth trends)" },
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
      <Header onLogoClick={() => {
        streamControllerRef.current?.abort()
        setAppState("idle")
        setQuery("")
        setAnalysisText("")
        setPackageStats([])
        setLineChartData([])
        setLineChartPackages([])
        setLoadingSteps([])
        window.scrollTo({ top: 0, behavior: "smooth" })
      }} />

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

        {appState === "loading" && (
          <section className="px-6 pb-6">
            <div className="max-w-5xl mx-auto flex flex-col gap-6">
              {/* Real-time pipeline steps — show last 4 max */}
              <Card className="shadow-sm py-4">
                <CardContent className="flex flex-col gap-3">
                  {loadingSteps.length === 0 ? (
                    <div className="flex items-center gap-3">
                      <Loader2 className="size-5 text-[#6366f1] animate-spin" />
                      <span className="text-sm text-foreground font-medium">
                        Connecting to RepoScout agent...
                      </span>
                    </div>
                  ) : (
                    <>
                      {loadingSteps.length > 4 && (
                        <span className="text-xs text-muted-foreground">
                          {loadingSteps.length - 4} earlier step{loadingSteps.length - 4 > 1 ? "s" : ""} completed
                        </span>
                      )}
                      {loadingSteps.slice(-4).map((step, i) => {
                        const isLast = i === Math.min(loadingSteps.length, 4) - 1
                        return (
                          <div key={step + i} className="flex items-center gap-3">
                            {isLast ? (
                              <Loader2 className="size-5 text-[#6366f1] animate-spin" />
                            ) : (
                              <div className="flex items-center justify-center size-5 rounded-full bg-[#10b981]">
                                <Check className="size-3 text-[#ffffff]" />
                              </div>
                            )}
                            <span
                              className={`text-sm ${
                                isLast ? "text-foreground font-medium" : "text-muted-foreground"
                              }`}
                            >
                              {step}
                            </span>
                          </div>
                        )
                      })}
                    </>
                  )}
                </CardContent>
              </Card>

              {/* Skeleton cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Card key={i} className="shadow-sm py-4">
                    <CardContent className="flex flex-col gap-2">
                      <Skeleton className="h-3 w-24" />
                      <Skeleton className="h-7 w-16" />
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Skeleton table */}
              <Card className="shadow-sm py-4">
                <CardContent className="flex flex-col gap-3">
                  <Skeleton className="h-4 w-48" />
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </CardContent>
              </Card>
            </div>
          </section>
        )}

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
