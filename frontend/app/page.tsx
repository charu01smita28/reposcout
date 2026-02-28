"use client"

import { useState, useEffect, useRef, useCallback } from "react"
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
import { type PackageData } from "@/lib/sample-data"

type AppState = "idle" | "loading" | "results"

export default function RepoScoutPage() {
  const [query, setQuery] = useState("")
  const [followUpQuery, setFollowUpQuery] = useState("")
  const [activeMode, setActiveMode] = useState("solve")
  const [appState, setAppState] = useState<AppState>("idle")
  const [selectedPackage, setSelectedPackage] = useState<string | null>(
    "slowapi"
  )
  const resultsRef = useRef<HTMLDivElement>(null)

  const handleSearch = useCallback(() => {
    if (!query.trim()) return
    setAppState("loading")
  }, [query])

  useEffect(() => {
    if (appState === "loading") {
      const timer = setTimeout(() => {
        setAppState("results")
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: "smooth" })
        }, 100)
      }, 3500)
      return () => clearTimeout(timer)
    }
  }, [appState])

  const handleSuggestionSelect = (suggestion: string) => {
    setQuery(suggestion)
    setTimeout(() => {
      setAppState("loading")
    }, 200)
  }

  const handleFollowUp = (text: string) => {
    setQuery(text)
    setFollowUpQuery("")
    setAppState("loading")
  }

  const handleSelectPackageFromTable = (pkg: PackageData) => {
    setSelectedPackage(pkg.name)
  }

  const handleSelectPackageFromMap = (name: string) => {
    setSelectedPackage(name)
  }

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
          <SuggestionCards onSelect={handleSuggestionSelect} />
        )}

        {appState === "loading" && <LoadingPipeline />}

        {appState === "results" && (
          <div ref={resultsRef} className="flex flex-col">
            <StatsBanner />
            <ComparisonTable
              onSelectPackage={handleSelectPackageFromTable}
              selectedPackage={selectedPackage}
            />
            <ChartsSection />
            <DependencyMap
              onSelectPackage={handleSelectPackageFromMap}
              selectedPackage={selectedPackage}
            />
            <PackageDeepDive />
            <AISynthesis onFollowUp={handleFollowUp} />
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
