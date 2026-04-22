import { Activity, BarChart3 } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency } from '@/lib/format'
import type { PerformanceSummary } from '@/types/trading'

export function PerformancePanels({ metrics }: { metrics: PerformanceSummary }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
      <Card>
        <CardHeader>
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="size-4 text-sky-300" />
              Equity curve
            </CardTitle>
            <CardDescription className="mt-1">Trend context without pulling attention away from execution.</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={metrics.equityCurve}>
              <defs>
                <linearGradient id="equityFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.42} />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis hide dataKey="time" />
              <YAxis hide domain={['dataMin - 400', 'dataMax + 400']} />
              <Tooltip
                formatter={(value) => formatCurrency(Number(value ?? 0))}
                labelFormatter={(value) => new Date(String(value)).toLocaleTimeString()}
                contentStyle={{
                  background: '#0b1118',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 18,
                }}
              />
              <Area dataKey="value" stroke="#38bdf8" strokeWidth={2.2} fill="url(#equityFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="size-4 text-emerald-300" />
              PnL distribution
            </CardTitle>
            <CardDescription className="mt-1">Bucketed outcomes surface variance quickly.</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={metrics.pnlDistribution}>
              <XAxis dataKey="bucket" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                contentStyle={{
                  background: '#0b1118',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 18,
                }}
              />
              <Bar dataKey="value" fill="#34d399" radius={[10, 10, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
