const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface SearchResponse {
  analysis: string
  tool_calls: ToolCall[]
  iterations: number
  mode: string
  packages: PackageStats[]
  search: Record<string, unknown> | null
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
  result_preview: string
}

export interface PackageStats {
  name: string
  found_in_db: boolean
  found_in_pypi: boolean
  stars: number
  forks: number
  dependents_count: number
  total_versions: number
  repository_url: string
  license: string
  latest_version: string
  summary: string
  author: string
  reposcout_score: number
  score_label: string
  score_color: string
  days_since_last_release: number
  growth_pct?: number
  code_snippet?: string
  code_source?: string
}

export interface QuickSearchResult {
  name: string
  summary: string
  stars: number
  dependent_count: number
  growth_pct: number
  version: string
  similarity_score: number
}

export interface DatasetStats {
  total_packages: number
  total_dependencies: number
  platforms: string[]
}

// --- API calls ---

export async function searchAgent(query: string, mode: string = "auto"): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, mode }),
  })
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`)
  return res.json()
}

export async function quickSearch(query: string, limit: number = 10): Promise<QuickSearchResult[]> {
  const res = await fetch(`${API_BASE}/api/search/quick?q=${encodeURIComponent(query)}&limit=${limit}`)
  if (!res.ok) throw new Error(`Quick search failed: ${res.statusText}`)
  return res.json()
}

export async function getPackageDetail(name: string): Promise<PackageStats> {
  const res = await fetch(`${API_BASE}/api/package/${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error(`Package not found: ${name}`)
  return res.json()
}

export async function getDatasetStats(): Promise<DatasetStats> {
  const res = await fetch(`${API_BASE}/api/stats`)
  if (!res.ok) throw new Error("Failed to fetch stats")
  return res.json()
}

export async function getHealthCheck(name: string) {
  const res = await fetch(`${API_BASE}/api/health/${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error(`Health check failed: ${name}`)
  return res.json()
}

export async function comparePackages(packages: string[]) {
  const res = await fetch(`${API_BASE}/api/compare?packages=${packages.join(",")}`)
  if (!res.ok) throw new Error("Comparison failed")
  return res.json()
}

export interface DownloadDataPoint {
  package_name: string
  month: string
  downloads: number
}

export function searchAgentStream(
  query: string,
  mode: string,
  onMetadata: (data: Omit<SearchResponse, "analysis">) => void,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  onProgress?: (step: string) => void,
  onDownloads?: (data: DownloadDataPoint[]) => void,
): AbortController {
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/search/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, mode }),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error(`Search failed: ${res.statusText}`)
      if (!res.body) throw new Error("No response body")

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events from buffer
        const lines = buffer.split("\n")
        buffer = lines.pop() || "" // Keep incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith("data: ")) continue

          const jsonStr = trimmed.slice(6)
          try {
            const event = JSON.parse(jsonStr)
            if (event.type === "progress") {
              onProgress?.(event.step)
            } else if (event.type === "metadata") {
              onMetadata({
                tool_calls: event.tool_calls,
                iterations: event.iterations,
                mode: event.mode,
                packages: event.packages || [],
                search: event.search,
              })
            } else if (event.type === "downloads") {
              onDownloads?.(event.data)
            } else if (event.type === "token") {
              onToken(event.content)
            } else if (event.type === "done") {
              onDone()
            }
          } catch {
            // Skip malformed JSON lines
          }
        }
      }

      // Process any remaining buffer
      if (buffer.trim().startsWith("data: ")) {
        try {
          const event = JSON.parse(buffer.trim().slice(6))
          if (event.type === "done") onDone()
        } catch {
          // ignore
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      onError(err instanceof Error ? err : new Error(String(err)))
    }
  })()

  return controller
}

export async function getDownloadTrends(packageNames: string[]): Promise<DownloadDataPoint[]> {
  const res = await fetch(`${API_BASE}/api/downloads?packages=${packageNames.join(",")}`)
  if (!res.ok) throw new Error("Download trends failed")
  return res.json()
}
