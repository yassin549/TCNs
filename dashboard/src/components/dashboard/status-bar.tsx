import { Activity, CircleAlert, Clock3, Plug, RadioTower, ShieldCheck } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { formatFreshness, formatDateTime } from '@/lib/format'
import type { LiveSessionMetadata } from '@/types/trading'

const toneMap = {
  healthy: 'healthy',
  caution: 'caution',
  critical: 'critical',
} as const

const statusMap = {
  LIVE: 'healthy',
  'DRY RUN': 'caution',
  PAUSED: 'outline',
  ERROR: 'critical',
} as const

export function StatusBar({
  session,
  usingMock,
}: {
  session: LiveSessionMetadata
  usingMock: boolean
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1.45fr)_repeat(5,minmax(0,1fr))]">
        <div className="flex items-start gap-4 rounded-[20px] border border-white/10 bg-white/[0.04] p-4">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-[18px] bg-[radial-gradient(circle,rgba(43,207,138,0.28),rgba(43,207,138,0.06))]">
            <ShieldCheck className="size-5 text-emerald-300" />
          </div>
          <div className="min-w-0 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={statusMap[session.mode]}>{session.mode}</Badge>
              <Badge variant={toneMap[session.health]}>health {session.health}</Badge>
              {usingMock ? <Badge variant="outline">mock feed</Badge> : null}
            </div>
            <div>
              <div className="text-base font-semibold text-white">System status</div>
              <p className="mt-1 text-sm text-slate-400">
                {session.currentSessionLabel} / {session.marketSession}
              </p>
            </div>
            <div className="grid gap-3 text-sm text-slate-400 sm:grid-cols-2">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Last update</div>
                <div className="mt-1 text-slate-200">{formatDateTime(session.lastUpdate)}</div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Freshness</div>
                <div className="mt-1 text-slate-200">{formatFreshness(session.lastUpdate)}</div>
              </div>
            </div>
          </div>
        </div>
        <StatusItem
          icon={Plug}
          label="Connection"
          value={session.connectionStatus}
          subValue="Gateway"
          tone={
            session.connectionStatus === 'connected'
              ? 'healthy'
              : session.connectionStatus === 'degraded'
                ? 'caution'
                : 'critical'
          }
        />
        <StatusItem
          icon={RadioTower}
          label="Broker"
          value={session.brokerStatus}
          subValue="Execution"
          tone={
            session.brokerStatus === 'connected'
              ? 'healthy'
              : session.brokerStatus === 'degraded'
                ? 'caution'
                : 'critical'
          }
        />
        <StatusItem
          icon={Clock3}
          label="Data freshness"
          value={`${session.dataFreshnessSeconds}s`}
          subValue={session.dataFreshnessSeconds < 30 ? 'healthy feed' : 'watch latency'}
          tone={
            session.dataFreshnessSeconds < 30
              ? 'healthy'
              : session.dataFreshnessSeconds < 90
                ? 'caution'
                : 'critical'
          }
        />
        <StatusItem
          icon={CircleAlert}
          label="Open positions"
          value={String(session.openPositions)}
          subValue={`${session.activeSignals} active signals`}
        />
        <StatusItem
          icon={ShieldCheck}
          label="Specialists"
          value={String(session.activeSpecialists)}
          subValue={`${session.rejectedSignals} rejects`}
        />
        <StatusItem
          icon={Activity}
          label="Session mode"
          value={session.mode.toLowerCase()}
          subValue={usingMock ? 'paper snapshot' : 'live monitor'}
          tone={statusMap[session.mode] === 'outline' ? 'neutral' : toneMap[session.health]}
        />
      </CardContent>
    </Card>
  )
}

function StatusItem({
  icon: Icon,
  label,
  value,
  subValue,
  tone = 'neutral',
}: {
  icon: typeof Plug
  label: string
  value: string
  subValue?: string
  tone?: 'neutral' | 'healthy' | 'caution' | 'critical'
}) {
  return (
    <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-4 flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-500">
        <Icon className="size-3.5" />
        {label}
      </div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-lg font-semibold capitalize text-white">{value}</div>
          {subValue ? <div className="mt-1 text-xs text-slate-500">{subValue}</div> : null}
        </div>
        {tone !== 'neutral' ? (
          <span
            className={
              tone === 'healthy'
                ? 'size-2.5 rounded-full bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,0.6)]'
                : tone === 'caution'
                  ? 'size-2.5 rounded-full bg-amber-400 shadow-[0_0_14px_rgba(251,191,36,0.6)]'
                  : 'size-2.5 rounded-full bg-rose-400 shadow-[0_0_14px_rgba(251,113,133,0.6)]'
            }
          />
        ) : null}
      </div>
    </div>
  )
}
