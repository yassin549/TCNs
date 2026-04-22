import { useMemo, useState } from 'react'

import { AlertTriangle, LoaderCircle } from 'lucide-react'

import { AllocatorPanel } from '@/components/dashboard/allocator-panel'
import { HealthPanel } from '@/components/dashboard/health-panel'
import { MetricCards } from '@/components/dashboard/metric-cards'
import { PerformancePanels } from '@/components/dashboard/performance-panels'
import { PriceChartPanel } from '@/components/dashboard/price-chart-panel'
import { SpecialistsPanel } from '@/components/dashboard/specialists-panel'
import { StatusBar } from '@/components/dashboard/status-bar'
import { TradeDetailsDrawer } from '@/components/dashboard/trade-details-drawer'
import { TradeJournal } from '@/components/dashboard/trade-journal'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useDashboardData } from '@/hooks/use-dashboard-data'
import type { Trade, TradeFilters } from '@/types/trading'

const initialFilters: TradeFilters = {
  symbol: 'all',
  specialist: 'all',
  outcome: 'all',
  session: 'all',
  regime: 'all',
  mode: 'all',
  startDate: '',
  endDate: '',
  search: '',
}

function App() {
  const { data, loading, error, source } = useDashboardData()
  const [symbol, setSymbol] = useState('US100')
  const [timeframe, setTimeframe] = useState('1m')
  const [selectedTradeId, setSelectedTradeId] = useState<string>()
  const [drawerTrade, setDrawerTrade] = useState<Trade | null>(null)
  const [filters, setFilters] = useState<TradeFilters>(initialFilters)

  const activeTrade = useMemo(
    () => data?.trades.find((trade) => trade.id === selectedTradeId) ?? null,
    [data?.trades, selectedTradeId],
  )

  if (loading) {
    return (
      <div className="min-h-screen px-4 py-6 text-white md:px-6 lg:px-8">
        <div className="mx-auto max-w-[1720px] space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_360px]">
            <Skeleton className="h-[48rem] w-full" />
            <div className="space-y-4">
              <Skeleton className="h-72 w-full" />
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-72 w-full" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 py-10">
        <Card className="max-w-xl">
          <CardContent className="space-y-4 p-8 text-center">
            <div className="mx-auto flex size-14 items-center justify-center rounded-[20px] bg-rose-500/10">
              <AlertTriangle className="size-6 text-rose-300" />
            </div>
            <div className="text-2xl font-semibold text-white">Dashboard feed unavailable</div>
            <p className="text-sm leading-6 text-slate-400">
              {error ?? 'The monitor could not load its current trading state.'}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const currentCandles = data.candlesBySymbol[symbol] ?? []

  return (
    <TooltipProvider>
      <div className="min-h-screen px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-[1720px] space-y-6">
          <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">Trading observability</Badge>
                <Badge variant={source === 'mock' ? 'critical' : 'healthy'}>
                  {source === 'api' ? 'live API' : source === 'local' ? 'local snapshot' : 'mock fallback'}
                </Badge>
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">
                  ML trading control room
                </h1>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                  High-signal visibility into system health, active price action, allocator pressure, specialist behavior,
                  and execution detail.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
              <span className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2">
                <LoaderCircle className="size-4 text-sky-300" />
                Auto-refreshing every 15s
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2 text-slate-300 transition hover:bg-white/[0.06]"
                  >
                    API wiring
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  Wire `VITE_API_BASE_URL` to use `/api/status`, `/api/metrics`, `/api/trades`, and live streams.
                </TooltipContent>
              </Tooltip>
            </div>
          </header>

          <StatusBar session={data.session} usingMock={source === 'mock'} />
          <MetricCards metrics={data.metrics} />

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_360px]">
            <PriceChartPanel
              symbol={symbol}
              symbols={data.session.symbols}
              timeframe={timeframe}
              timeframes={data.session.timeframes}
              candles={currentCandles}
              trades={data.trades}
              selectedTradeId={selectedTradeId}
              onSelectedTradeChange={setSelectedTradeId}
              onSymbolChange={setSymbol}
              onTimeframeChange={setTimeframe}
              onMarkerSelect={(trade) => setDrawerTrade(trade)}
            />
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              <SpecialistsPanel specialists={data.specialists} />
              <AllocatorPanel allocator={data.allocator} />
              <HealthPanel checks={data.healthChecks} />
            </div>
          </div>

          <PerformancePanels metrics={data.metrics} />
          <TradeJournal
            trades={data.trades}
            filters={filters}
            onFiltersChange={setFilters}
            onTradeSelect={(trade) => setDrawerTrade(trade)}
          />
        </div>
      </div>
      <TradeDetailsDrawer
        trade={drawerTrade ?? activeTrade}
        open={Boolean(drawerTrade ?? activeTrade)}
        onOpenChange={(open) => {
          if (!open) {
            setDrawerTrade(null)
            setSelectedTradeId(undefined)
          }
        }}
      />
    </TooltipProvider>
  )
}

export default App
