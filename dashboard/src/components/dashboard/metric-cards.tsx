import { ChevronDown } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { formatCurrency, formatPercent, formatSigned } from '@/lib/format'
import type { PerformanceSummary } from '@/types/trading'

function formatNullable(value: number | null, formatter: (resolved: number) => string) {
  return value === null ? 'n/a' : formatter(value)
}

const primaryItems = [
  {
    key: 'totalPnl',
    label: 'Total PnL',
    description: 'Realized performance',
    format: (value: number | null) => formatNullable(value, formatCurrency),
  },
  {
    key: 'dailyPnl',
    label: 'Daily PnL',
    description: 'Current session',
    format: (value: number | null) => formatNullable(value, formatCurrency),
  },
  {
    key: 'winRate',
    label: 'Win rate',
    description: 'Closed trades',
    format: (value: number | null) => formatNullable(value, formatPercent),
  },
  {
    key: 'profitFactor',
    label: 'Profit factor',
    description: 'Gross win / loss',
    format: (value: number | null) => formatNullable(value, (resolved) => resolved.toFixed(2)),
  },
  {
    key: 'openRisk',
    label: 'Open risk',
    description: 'Portfolio at risk',
    format: (value: number | null) => formatNullable(value, formatPercent),
  },
  {
    key: 'activeSignals',
    label: 'Active signals',
    description: 'Pending actions',
    format: (value: number | null) => formatNullable(value, String),
  },
] as const

const supportingItems = [
  { key: 'weeklyPnl', label: 'Weekly PnL', format: (value: number | null) => formatNullable(value, formatCurrency) },
  { key: 'maxDrawdown', label: 'Max drawdown', format: (value: number | null) => formatNullable(value, formatPercent) },
  { key: 'expectancy', label: 'Expectancy', format: (value: number | null) => formatNullable(value, (resolved) => `${formatSigned(resolved)}R`) },
  { key: 'trades', label: 'Trades', format: (value: number | null) => formatNullable(value, String) },
  { key: 'averageR', label: 'Avg R / trade', format: (value: number | null) => formatNullable(value, (resolved) => `${formatSigned(resolved)}R`) },
  { key: 'exposure', label: 'Exposure', format: (value: number | null) => formatNullable(value, formatPercent) },
  { key: 'slippage', label: 'Slippage', format: (value: number | null) => formatNullable(value, (resolved) => `${resolved.toFixed(1)} bps`) },
  { key: 'fillQuality', label: 'Fill quality', format: (value: number | null) => formatNullable(value, formatPercent) },
  { key: 'rejectedSignals', label: 'Rejected signals', format: (value: number | null) => formatNullable(value, String) },
] as const

export function MetricCards({ metrics }: { metrics: PerformanceSummary }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        {primaryItems.map((item) => (
          <Card key={item.key}>
            <CardContent className="space-y-4 p-5">
              <div className="space-y-1">
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{item.label}</div>
                <div className="text-xs text-slate-500">{item.description}</div>
              </div>
              <div className={metricValueTone(item.key, metrics[item.key])}>{item.format(metrics[item.key])}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between rounded-[24px] border border-white/8 bg-white/[0.03] px-5 py-4 text-left transition hover:bg-white/[0.05]">
          <div className="space-y-1">
            <div className="text-sm font-semibold text-white">Supporting diagnostics</div>
            <div className="text-sm text-slate-400">Secondary metrics stay available without crowding the primary view.</div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline">{supportingItems.length} metrics</Badge>
            <ChevronDown className="size-4 text-slate-400 transition group-open:rotate-180" />
          </div>
        </summary>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {supportingItems.map((item) => (
            <Card key={item.key} className="bg-white/[0.02] shadow-none">
              <CardContent className="space-y-3 p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{item.label}</div>
                <div className={metricValueTone(item.key, metrics[item.key], true)}>{item.format(metrics[item.key])}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </details>
    </div>
  )
}

function metricValueTone(
  key: keyof PerformanceSummary,
  value: number | null,
  compact = false,
) {
  const base = compact ? 'text-xl font-semibold' : 'text-[30px] font-semibold leading-none'

  if (typeof value !== 'number') {
    return `${base} text-white`
  }

  if (key === 'totalPnl' || key === 'dailyPnl' || key === 'weeklyPnl') {
    return `${base} ${value >= 0 ? 'text-emerald-300' : 'text-rose-300'}`
  }

  if (key === 'maxDrawdown' || key === 'openRisk' || key === 'exposure' || key === 'slippage' || key === 'rejectedSignals') {
    return `${base} text-white`
  }

  return `${base} text-white`
}
