"use client"

import { useEffect, useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent } from "@/components/ui/card"
import { loadingSteps } from "@/lib/sample-data"

export function LoadingPipeline() {
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= loadingSteps.length - 1) {
          clearInterval(interval)
          return prev
        }
        return prev + 1
      })
    }, 800)

    return () => clearInterval(interval)
  }, [])

  return (
    <section className="px-6 pb-6">
      <div className="max-w-5xl mx-auto flex flex-col gap-6">
        {/* Pipeline steps */}
        <Card className="shadow-sm py-4">
          <CardContent className="flex flex-col gap-3">
            {loadingSteps.map((step, index) => (
              <div key={step} className="flex items-center gap-3">
                {index < currentStep ? (
                  <div className="flex items-center justify-center size-5 rounded-full bg-[#10b981]">
                    <Check className="size-3 text-[#ffffff]" />
                  </div>
                ) : index === currentStep ? (
                  <Loader2 className="size-5 text-[#6366f1] animate-spin" />
                ) : (
                  <div className="size-5 rounded-full border-2 border-border" />
                )}
                <span
                  className={`text-sm ${
                    index <= currentStep
                      ? "text-foreground"
                      : "text-muted-foreground"
                  }`}
                >
                  {step}
                </span>
              </div>
            ))}
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

        {/* Skeleton charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="shadow-sm py-4">
            <CardContent className="flex flex-col gap-2">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-[240px] w-full" />
            </CardContent>
          </Card>
          <Card className="shadow-sm py-4">
            <CardContent className="flex flex-col gap-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-[240px] w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}
