import { ShieldHalf } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatPercent } from '@/lib/format'
import type { AllocatorStats } from '@/types/trading'

export function AllocatorPanel({ allocator }: { allocator: AllocatorStats }) {
  const riskUtilization = Math.min(100, (allocator.currentPortfolioRisk / allocator.maxAllowedRisk) * 100)

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldHalf className="size-4 text-sky-300" />
            Portfolio allocator
          </CardTitle>
          <CardDescription className="mt-1">
            Capacity, risk budget, and rejection pressure in one compact block.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Kpi label="Candidates" value={String(allocator.totalCandidates)} />
          <Kpi label="Accepted" value={String(allocator.acceptedTrades)} />
          <Kpi label="Rejected" value={String(allocator.rejectedTrades)} />
          <Kpi label="Concurrent" value={String(allocator.concurrentPositions)} />
        </div>

        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-white">Portfolio risk</div>
              <div className="mt-1 text-sm text-slate-400">
                {formatPercent(allocator.currentPortfolioRisk)} active / {formatPercent(allocator.maxAllowedRisk)} max
              </div>
            </div>
            <Badge variant={allocator.jointAllocationHealthy ? 'healthy' : 'critical'}>
              {allocator.jointAllocationHealthy ? 'healthy' : 'drifting'}
            </Badge>
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-slate-500">
              <span>Risk utilization</span>
              <span>{riskUtilization.toFixed(0)}%</span>
            </div>
            <div className="h-2.5 rounded-full bg-white/5">
              <div
                className={`h-2.5 rounded-full ${
                  allocator.jointAllocationHealthy
                    ? 'bg-[linear-gradient(90deg,#38bdf8,#34d399)]'
                    : 'bg-[linear-gradient(90deg,#f59e0b,#fb7185)]'
                }`}
                style={{ width: `${riskUtilization}%` }}
              />
            </div>
          </div>
        </div>

        <div className="space-y-3 rounded-[20px] border border-white/10 bg-white/[0.03] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Risk by instrument</div>
          {allocator.riskByInstrument.map((row) => (
            <div key={row.symbol} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-200">{row.symbol}</span>
                <span className="text-slate-500">
                  {formatPercent(row.allocatedRiskPct)} / {row.signals} signals
                </span>
              </div>
              <div className="h-2 rounded-full bg-white/5">
                <div className="h-2 rounded-full bg-sky-400" style={{ width: `${row.allocatedRiskPct * 100}%` }} />
              </div>
            </div>
          ))}
        </div>

        <details className="group rounded-[20px] border border-white/10 bg-white/[0.03]">
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3">
            <div>
              <div className="text-sm font-medium text-white">Rejection reasons</div>
              <div className="mt-1 text-sm text-slate-400">Open only when investigating allocation pressure.</div>
            </div>
            <Badge variant="outline">{allocator.rejectionReasons.length}</Badge>
          </summary>
          <div className="space-y-2 border-t border-white/6 px-4 pb-4 pt-3">
            {allocator.rejectionReasons.map((reason) => (
              <div
                key={reason.reason}
                className="flex items-center justify-between rounded-[16px] border border-white/6 bg-white/[0.02] px-3 py-2 text-sm"
              >
                <span className="text-slate-300">{reason.reason}</span>
                <span className="text-slate-500">{reason.count}</span>
              </div>
            ))}
          </div>
        </details>
      </CardContent>
    </Card>
  )
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[18px] border border-white/10 bg-white/[0.03] p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
    </div>
  )
}
