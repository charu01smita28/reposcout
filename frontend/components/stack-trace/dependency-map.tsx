"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { dependencyTree } from "@/lib/sample-data"

function HealthDot({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-[#10b981]"
      : score >= 60
        ? "bg-[#f59e0b]"
        : "bg-[#ef4444]"
  return <span className={`inline-block size-2.5 rounded-full ${color}`} />
}

interface TreeNodeProps {
  node: (typeof dependencyTree.children)[0]
  onSelect: (name: string) => void
  selected: string | null
}

function TreeNode({ node, onSelect, selected }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const isSelected = selected === node.name

  return (
    <div className="ml-4">
      <button
        onClick={() => {
          setExpanded(!expanded)
          onSelect(node.name)
        }}
        className={`flex items-center gap-2 py-1.5 px-2 rounded-md w-full text-left transition-colors cursor-pointer ${
          isSelected ? "bg-[#eef2ff]" : "hover:bg-muted"
        }`}
      >
        {expanded ? (
          <ChevronDown className="size-3.5 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="size-3.5 text-muted-foreground shrink-0" />
        )}
        <HealthDot score={node.health} />
        <span className="font-mono font-bold text-sm text-[#6366f1]">
          {node.name}
        </span>
        <span className="text-xs text-muted-foreground">
          ({node.dependents.toLocaleString()} dependents)
        </span>
      </button>

      {expanded && (
        <div className="ml-8 border-l-2 border-border pl-3 py-1 flex flex-col gap-1">
          {node.dependencies.map((dep) => (
            <div key={dep} className="flex items-center gap-2 py-0.5">
              <span className="text-xs text-muted-foreground">depends on:</span>
              <span className="font-mono text-xs text-foreground">{dep}</span>
            </div>
          ))}
          <div className="flex items-center gap-2 py-0.5">
            <span className="text-xs text-muted-foreground">used by:</span>
            <span className="font-mono text-xs text-foreground">
              {node.usedBy}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

interface DependencyMapProps {
  onSelectPackage: (name: string) => void
  selectedPackage: string | null
}

export function DependencyMap({
  onSelectPackage,
  selectedPackage,
}: DependencyMapProps) {
  return (
    <section className="px-6 pb-6">
      <Card className="shadow-sm max-w-5xl mx-auto py-0">
        <CardHeader className="pb-0 pt-5">
          <CardTitle className="text-base">Dependency Map</CardTitle>
        </CardHeader>
        <CardContent className="pt-4 pb-5">
          <div className="flex items-center gap-2 py-2 px-2 mb-2">
            <span className="inline-flex items-center justify-center size-7 rounded-lg bg-[#6366f1] text-[#ffffff] text-xs font-bold">
              RL
            </span>
            <span className="font-semibold text-sm text-foreground">
              {dependencyTree.name}
            </span>
          </div>
          <div className="flex flex-col">
            {dependencyTree.children.map((child) => (
              <TreeNode
                key={child.name}
                node={child}
                onSelect={onSelectPackage}
                selected={selectedPackage}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
