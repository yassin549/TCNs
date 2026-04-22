import { AlertTriangle, ChevronDown } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateTime } from '@/lib/format'
import type { HealthCheck } from '@/types/trading'

const severityRank = {
  critical: 0,
  caution: 1,
  healthy: 2,
} as const

export function HealthPanel({ checks }: { checks: HealthCheck[] }) {
  const sorted = [...checks].sort((left, right) => severityRank[left.severity] - severityRank[right.severity])
  const priorityChecks = sorted.filter((check) => check.severity !== 'healthy')
  const backgroundChecks = sorted.filter((check) => check.severity === 'healthy')

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangle className="size-4 text-amber-300" />
            Health and anomalies
          </CardTitle>
          <CardDescription className="mt-1">
            Critical issues stay on top. Healthy confirmations stay collapsed unless you need them.
          </CardDescription>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={priorityChecks.some((check) => check.severity === 'critical') ? 'critical' : 'healthy'}>
            {priorityChecks.filter((check) => check.severity === 'critical').length} critical
          </Badge>
          <Badge variant={priorityChecks.some((check) => check.severity === 'caution') ? 'caution' : 'outline'}>
            {priorityChecks.filter((check) => check.severity === 'caution').length} warnings
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {priorityChecks.length ? (
          priorityChecks.map((check) => <HealthRow key={check.id} check={check} />)
        ) : (
          <div className="rounded-[20px] border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
            No active warnings. The system is reporting healthy conditions across monitored checks.
          </div>
        )}

        {backgroundChecks.length ? (
          <details className="group rounded-[20px] border border-white/10 bg-white/[0.03]">
            <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3">
              <div>
                <div className="text-sm font-medium text-white">Healthy checks</div>
                <div className="mt-1 text-sm text-slate-400">Folded to keep the panel focused.</div>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="outline">{backgroundChecks.length}</Badge>
                <ChevronDown className="size-4 text-slate-400 transition group-open:rotate-180" />
              </div>
            </summary>
            <div className="space-y-2 border-t border-white/6 px-4 pb-4 pt-3">
              {backgroundChecks.map((check) => (
                <HealthRow key={check.id} check={check} compact />
              ))}
            </div>
          </details>
        ) : null}
      </CardContent>
    </Card>
  )
}

function HealthRow({ check, compact = false }: { check: HealthCheck; compact?: boolean }) {
  return (
    <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="font-medium text-white">{check.title}</div>
          <p className={`${compact ? 'text-sm leading-5' : 'text-sm leading-6'} text-slate-400`}>
            {check.description}
          </p>
        </div>
        <Badge
          variant={
            check.severity === 'healthy'
              ? 'healthy'
              : check.severity === 'caution'
                ? 'caution'
                : 'critical'
          }
        >
          {check.severity}
        </Badge>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
        <span>{formatDateTime(check.timestamp)}</span>
        {check.action ? <span className="text-slate-400">{check.action}</span> : null}
      </div>
    </div>
  )
}
