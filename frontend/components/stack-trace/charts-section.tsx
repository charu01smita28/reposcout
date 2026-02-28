"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

interface ChartsSectionProps {
  barData: { name: string; dependents: number }[]
}

export function ChartsSection({ barData }: ChartsSectionProps) {
  return (
    <section className="px-6 pb-6">
      <div className="max-w-5xl mx-auto">
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
      </div>
    </section>
  )
}
