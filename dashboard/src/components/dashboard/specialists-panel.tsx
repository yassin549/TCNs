import { ActivitySquare, ChevronDown, TriangleAlert } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateTime, formatPercent, formatSigned } from '@/lib/format'
import type { SpecialistStats } from '@/types/trading'

function formatNullable(value: number | null, formatter: (resolved: number) => string) {
  return value === null ? 'n/a' : formatter(value)
}

const healthPriority = {
  critical: 0,
  caution: 1,
  healthy: 2,
} as const

export function SpecialistsPanel({ specialists }: { specialists: SpecialistStats[] }) {
  const sorted = [...specialists].sort((left, right) => {
    const healthGap = healthPriority[left.health] - healthPriority[right.health]
    if (healthGap !== 0) return healthGap
    return right.usagePct - left.usagePct
  })

  const dominantSpecialist = [...specialists].sort((left, right) => right.usagePct - left.usagePct)[0]?.key

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <ActivitySquare className="size-4 text-emerald-300" />
            Specialists
          </CardTitle>
          <CardDescription className="mt-1">
            Utilization, edge, and health are visible at a glance. Deeper context stays folded.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {sorted.map((specialist) => {
          const isDominant = specialist.key === dominantSpecialist
          const isFailing = specialist.health === 'critical' || !specialist.enabled

          return (
            <details key={specialist.key} className="group rounded-[20px] border border-white/10 bg-white/[0.03]">
              <summary className="flex cursor-pointer list-none flex-col gap-4 p-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0 space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="font-medium text-white">{specialist.key}</div>
                    {isDominant ? <Badge variant="healthy">dominant</Badge> : null}
                    {specialist.underweight ? <Badge variant="caution">underweight</Badge> : null}
                    {!specialist.enabled ? <Badge variant="critical">disabled</Badge> : null}
                    {isFailing ? (
                      <span className="inline-flex items-center gap-1 text-xs text-rose-300">
                        <TriangleAlert className="size-3.5" />
                        attention
                      </span>
                    ) : null}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <SummaryStat label="Usage" value={formatPercent(specialist.usagePct, 1)} />
                    <SummaryStat
                      label="Win rate"
                      value={formatNullable(specialist.winRate, (value) => formatPercent(value, 1))}
                    />
                    <SummaryStat
                      label="Avg R"
                      value={formatNullable(specialist.averageR, (value) => `${formatSigned(value)}R`)}
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-slate-500">
                      <span>Usage share</span>
                      <span>{specialist.usageCount} signals</span>
                    </div>
                    <div className="h-2 rounded-full bg-white/5">
                      <div
                        className={`h-2 rounded-full ${barTone(specialist.health)}`}
                        style={{ width: `${Math.max(6, specialist.usagePct * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 self-start lg:self-center">
                  <Badge
                    variant={
                      specialist.health === 'healthy'
                        ? 'healthy'
                        : specialist.health === 'caution'
                          ? 'caution'
                          : 'critical'
                    }
                  >
                    {specialist.health}
                  </Badge>
                  <ChevronDown className="size-4 text-slate-400 transition group-open:rotate-180" />
                </div>
              </summary>
              <div className="border-t border-white/6 px-4 pb-4 pt-4">
                <div className="grid gap-3 lg:grid-cols-2">
                  <div className="space-y-3 rounded-[18px] border border-white/8 bg-slate-950/35 p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Execution profile</div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Detail label="Accepted / rejected" value={`${specialist.acceptedSignals} / ${specialist.rejectedSignals}`} />
                      <Detail label="Last used" value={formatDateTime(specialist.lastUsed)} />
                    </div>
                    {specialist.rollingPerformance.length ? (
                      <div className="space-y-2">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Rolling performance</div>
                        <div className="flex h-24 items-end gap-1 rounded-[18px] border border-white/6 bg-slate-950/60 p-3">
                          {specialist.rollingPerformance.map((point, index) => (
                            <div
                              key={`${specialist.key}-${index}`}
                              className={`w-full rounded-full ${point >= 0 ? 'bg-emerald-400/85' : 'bg-rose-400/85'}`}
                              style={{ height: `${Math.max(10, Math.min(72, Math.abs(point) * 70))}px` }}
                            />
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-[18px] border border-white/6 bg-slate-950/50 p-3 text-sm text-slate-500">
                        No closed live trades yet for rolling realized performance.
                      </div>
                    )}
                  </div>
                  <div className="space-y-3 rounded-[18px] border border-white/8 bg-slate-950/35 p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Best context slices</div>
                    {specialist.bestContexts.length ? (
                      <div className="space-y-2">
                        {specialist.bestContexts.map((slice) => (
                          <div
                            key={slice.label}
                            className="rounded-[18px] border border-white/6 bg-white/[0.02] p-3 text-sm"
                          >
                            <div className="text-slate-200">{slice.label}</div>
                            <div className="mt-1 text-xs text-slate-500">
                              edge {slice.edge.toFixed(2)} / win{' '}
                              {formatNullable(slice.winRate, (value) => formatPercent(value, 1))}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-[18px] border border-white/6 bg-white/[0.02] p-3 text-sm text-slate-500">
                        No stable live context slices are available yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </details>
          )
        })}
      </CardContent>
    </Card>
  )
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-white/8 bg-slate-950/35 px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-medium text-white">{value}</div>
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-white/6 bg-white/[0.02] p-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-sm text-white">{value}</div>
    </div>
  )
}

function barTone(health: SpecialistStats['health']) {
  if (health === 'healthy') return 'bg-[linear-gradient(90deg,#38bdf8,#34d399)]'
  if (health === 'caution') return 'bg-[linear-gradient(90deg,#f59e0b,#fbbf24)]'
  return 'bg-[linear-gradient(90deg,#fb7185,#ef4444)]'
}
