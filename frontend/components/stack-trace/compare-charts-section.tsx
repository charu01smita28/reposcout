"use client"

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { barChartData, lineChartData, frameworkCompareData } from "@/lib/sample-data"

// Compare mode chart data
const frameworkBarData = frameworkCompareData.map((fw) => ({
  name: fw.name,
  downloads: fw.weeklyDownloads,
}))

const frameworkTrendData = [
  { month: "Mar", FastAPI: 8200000, Django: 9200000, Flask: 29500000 },
  { month: "Jun", FastAPI: 9800000, Django: 9400000, Flask: 29200000 },
  { month: "Sep", FastAPI: 11200000, Django: 9600000, Flask: 28800000 },
  { month: "Dec", FastAPI: 12500000, Django: 9800000, Flask: 28500000 },
]

interface ChartsSectionProps {
  isCompareMode?: boolean
}

export function ChartsSection({ isCompareMode = false }: ChartsSectionProps) {
  return (
    <section className="px-6 pb-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-5xl mx-auto">
        {/* Adoption Bar Chart */}
        <Card className="shadow-sm py-0">
          <CardHeader className="pb-0 pt-5">
            <CardTitle className="text-base">
              {isCompareMode ? "Weekly Downloads" : "Adoption (by dependents)"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 pb-5">
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={isCompareMode ? frameworkBarData : barChartData}
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
                      v >= 1000000 ? `${(v / 1000000).toFixed(0)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v
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
                      isCompareMode ? "Downloads" : "Dependents",
                    ]}
                  />
                  <Bar
                    dataKey={isCompareMode ? "downloads" : "dependents"}
                    fill="#6366f1"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Growth Trend Line Chart */}
        <Card className="shadow-sm py-0">
          <CardHeader className="pb-0 pt-5">
            <CardTitle className="text-base">
              {isCompareMode ? "Downloads Trend (Quarterly)" : "Growth Trend"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 pb-5">
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={isCompareMode ? frameworkTrendData : lineChartData}
                  margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#e2e8f0"
                  />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 12, fill: "#64748b" }}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: "#64748b" }}
                    tickFormatter={(v) =>
                      v >= 1000000 ? `${(v / 1000000).toFixed(0)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v
                    }
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
                      "",
                    ]}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: "12px" }}
                    iconType="circle"
                    iconSize={8}
                  />
                  {isCompareMode ? (
                    <>
                      <Line
                        type="monotone"
                        dataKey="FastAPI"
                        stroke="#6366f1"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="Django"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="Flask"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                    </>
                  ) : (
                    <>
                      <Line
                        type="monotone"
                        dataKey="ratelimit"
                        stroke="#6366f1"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="slowapi"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="flask-limiter"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                    </>
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
