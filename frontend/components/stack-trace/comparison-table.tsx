"use client"

import { Star, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table"
import { packageData, type PackageData } from "@/lib/sample-data"

function HealthBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-[#dcfce7] text-[#15803d] border-[#bbf7d0]"
      : score >= 60
        ? "bg-[#fef9c3] text-[#a16207] border-[#fde68a]"
        : "bg-[#fee2e2] text-[#dc2626] border-[#fecaca]"

  return (
    <span
      className={`inline-flex items-center justify-center size-9 rounded-full text-xs font-bold border ${color}`}
    >
      {score}
    </span>
  )
}

function ReleaseStatus({
  text,
  status,
}: {
  text: string
  status: "green" | "amber" | "red"
}) {
  const color =
    status === "green"
      ? "text-[#15803d]"
      : status === "amber"
        ? "text-[#a16207]"
        : "text-[#dc2626]"
  return <span className={`text-sm ${color}`}>{text}</span>
}

function TrendIndicator({
  value,
  direction,
}: {
  value: number
  direction: "up" | "down" | "neutral"
}) {
  if (direction === "up")
    return (
      <span className="flex items-center gap-1 text-[#15803d] text-sm font-medium">
        <ArrowUpRight className="size-3.5" />
        {value}%
      </span>
    )
  if (direction === "down")
    return (
      <span className="flex items-center gap-1 text-[#dc2626] text-sm font-medium">
        <ArrowDownRight className="size-3.5" />
        {value}%
      </span>
    )
  return (
    <span className="flex items-center gap-1 text-muted-foreground text-sm font-medium">
      <Minus className="size-3.5" />
      {value}%
    </span>
  )
}

interface ComparisonTableProps {
  onSelectPackage: (pkg: PackageData) => void
  selectedPackage: string | null
}

export function ComparisonTable({
  onSelectPackage,
  selectedPackage,
}: ComparisonTableProps) {
  return (
    <section className="px-6 pb-6">
      <Card className="shadow-sm max-w-5xl mx-auto py-0">
        <CardHeader className="pb-0 pt-5">
          <CardTitle className="text-base">Top Packages Comparison</CardTitle>
        </CardHeader>
        <CardContent className="pt-4 pb-2">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Package
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Dependents
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Stars
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Health
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Last Release
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Trend
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {packageData.map((pkg) => (
                <TableRow
                  key={pkg.name}
                  onClick={() => onSelectPackage(pkg)}
                  className={`cursor-pointer transition-colors ${
                    selectedPackage === pkg.name
                      ? "bg-[#eef2ff]"
                      : "hover:bg-[#f8f9ff]"
                  }`}
                >
                  <TableCell className="font-mono font-bold text-[#6366f1]">
                    {pkg.name}
                  </TableCell>
                  <TableCell className="text-foreground">
                    {pkg.dependents.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1 text-foreground">
                      <Star className="size-3.5 text-[#f59e0b] fill-[#f59e0b]" />
                      {pkg.stars.toLocaleString()}
                    </span>
                  </TableCell>
                  <TableCell>
                    <HealthBadge score={pkg.health} />
                  </TableCell>
                  <TableCell>
                    <ReleaseStatus
                      text={pkg.lastRelease}
                      status={pkg.lastReleaseStatus}
                    />
                  </TableCell>
                  <TableCell>
                    <TrendIndicator
                      value={pkg.trend}
                      direction={pkg.trendDirection}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </section>
  )
}
