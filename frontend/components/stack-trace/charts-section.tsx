"use client"

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  Legend,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

const LINE_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

interface ChartsSectionProps {
  barData: { name: string; dependents: number }[]
  lineData?: Record<string, string | number>[]
  packageNames?: string[]
}

function formatDownloads(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}k`
  return String(v)
}

export function ChartsSection({ barData, lineData, packageNames }: ChartsSectionProps) {
  const hasLineData = lineData && lineData.length > 0 && packageNames && packageNames.length > 0

  return (
    <section className="px-6 pb-6">
      <div className="max-w-5xl mx-auto">
        <div className={`grid gap-6 ${hasLineData ? "md:grid-cols-2" : "grid-cols-1"}`}>
          <Card className="shadow-sm py-0">
            <CardHeader className="pb-0 pt-5">
              <CardTitle className="text-base">
                Adoption (by dependents)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 pb-5">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={barData}
                    layout="vertical"
                    margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#e2e8f0"
                      horizontal={false}
                    />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 12, fill: "#64748b" }}
                      tickFormatter={(v) =>
                        v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v
                      }
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 12, fill: "#64748b", fontFamily: "var(--font-mono)" }}
                      width={110}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#ffffff",
                        border: "1px solid #e2e8f0",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(value: number) => [
                        value.toLocaleString(),
                        "Dependents",
                      ]}
                    />
                    <Bar
                      dataKey="dependents"
                      fill="#6366f1"
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {hasLineData && (
            <Card className="shadow-sm py-0">
              <CardHeader className="pb-0 pt-5">
                <CardTitle className="text-base">
                  Monthly Downloads
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 pb-5">
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={lineData}
                      margin={{ top: 5, right: 20, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="month"
                        tick={{ fontSize: 11, fill: "#64748b" }}
                      />
                      <YAxis
                        tick={{ fontSize: 12, fill: "#64748b" }}
                        tickFormatter={formatDownloads}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#ffffff",
                          border: "1px solid #e2e8f0",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        formatter={(value: number) => [
                          value.toLocaleString(),
                          "Downloads",
                        ]}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: "12px" }}
                      />
                      {packageNames.map((name, i) => (
                        <Line
                          key={name}
                          type="monotone"
                          dataKey={name}
                          stroke={LINE_COLORS[i % LINE_COLORS.length]}
                          strokeWidth={2}
                          dot={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </section>
  )
}
