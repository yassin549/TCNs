import { type ReactNode, startTransition, useDeferredValue, useMemo, useState } from 'react'

import { Filter, Search, X } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatCurrency, formatDateTime, formatSigned } from '@/lib/format'
import type { Trade, TradeFilters } from '@/types/trading'

const defaultFilters: TradeFilters = {
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

export function TradeJournal({
  trades,
  filters,
  onFiltersChange,
  onTradeSelect,
}: {
  trades: Trade[]
  filters: TradeFilters
  onFiltersChange: (next: TradeFilters) => void
  onTradeSelect: (trade: Trade) => void
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  const deferredSearch = useDeferredValue(filters.search)
  const symbols = useMemo(() => ['all', ...new Set(trades.map((trade) => trade.symbol))], [trades])
  const specialists = useMemo(() => ['all', ...new Set(trades.map((trade) => trade.specialist))], [trades])
  const sessions = useMemo(() => ['all', ...new Set(trades.map((trade) => trade.session))], [trades])
  const regimes = useMemo(() => ['all', ...new Set(trades.map((trade) => trade.regime))], [trades])

  const filtered = useMemo(() => {
    return trades.filter((trade) => {
      const query = deferredSearch.toLowerCase()
      return (
        (filters.symbol === 'all' || trade.symbol === filters.symbol) &&
        (filters.specialist === 'all' || trade.specialist === filters.specialist) &&
        (filters.outcome === 'all' || trade.outcome === filters.outcome) &&
        (filters.session === 'all' || trade.session === filters.session) &&
        (filters.regime === 'all' || trade.regime === filters.regime) &&
        (filters.mode === 'all' || trade.status === filters.mode) &&
        (!filters.startDate || trade.entryTime >= new Date(filters.startDate).toISOString()) &&
        (!filters.endDate || trade.entryTime <= new Date(`${filters.endDate}T23:59:59`).toISOString()) &&
        (!query || `${trade.symbol} ${trade.specialist} ${trade.context}`.toLowerCase().includes(query))
      )
    })
  }, [deferredSearch, filters, trades])

  const activeFilterCount = countActiveFilters(filters)
  const recentTrades = filtered.slice(0, 3)

  function patchFilters(next: Partial<TradeFilters>) {
    startTransition(() => {
      onFiltersChange({ ...filters, ...next })
    })
  }

  function resetFilters() {
    startTransition(() => {
      onFiltersChange(defaultFilters)
    })
  }

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="size-4 text-slate-300" />
            Trade journal
          </CardTitle>
          <CardDescription className="mt-1">
            Logs stay out of the way by default. The full table opens when you need to inspect execution detail.
          </CardDescription>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {activeFilterCount ? <Badge variant="caution">{activeFilterCount} active filters</Badge> : null}
          <Badge variant="outline">{filtered.length} trades</Badge>
          <Button variant={isExpanded ? 'primary' : 'ghost'} onClick={() => setIsExpanded((current) => !current)}>
            {isExpanded ? 'Hide journal' : 'Open journal'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isExpanded ? (
          <div className="grid gap-3 lg:grid-cols-3">
            {recentTrades.length ? (
              recentTrades.map((trade) => (
                <button
                  key={trade.id}
                  type="button"
                  onClick={() => onTradeSelect(trade)}
                  className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4 text-left transition hover:bg-white/[0.05]"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-white">
                      {trade.symbol} / {trade.specialist}
                    </div>
                    <Badge
                      variant={
                        trade.outcome === 'win'
                          ? 'healthy'
                          : trade.outcome === 'loss'
                            ? 'critical'
                            : 'caution'
                      }
                    >
                      {trade.outcome}
                    </Badge>
                  </div>
                  <div className="mt-3 grid gap-2 text-sm text-slate-400">
                    <span>{formatDateTime(trade.entryTime)}</span>
                    <span>{trade.context}</span>
                    <span className={trade.pnlR >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                      {formatCurrency(trade.pnl)} / {formatSigned(trade.pnlR)}R
                    </span>
                  </div>
                </button>
              ))
            ) : (
              <div className="lg:col-span-3 rounded-[20px] border border-white/10 bg-white/[0.03] p-5 text-sm text-slate-500">
                No executed trades match the current filters. Open the journal to adjust the filter set.
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="space-y-3 rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                <FilterField label="Search" active={Boolean(filters.search)}>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
                    <Input
                      value={filters.search}
                      onChange={(event) => patchFilters({ search: event.target.value })}
                      placeholder="Symbol, specialist, context"
                      className={`pl-10 ${filters.search ? 'border-sky-400/35 bg-sky-400/10' : ''}`}
                    />
                  </div>
                </FilterField>
                <FilterSelect
                  label="Symbol"
                  value={filters.symbol}
                  onChange={(value) => patchFilters({ symbol: value })}
                  items={symbols}
                  active={filters.symbol !== 'all'}
                />
                <FilterSelect
                  label="Specialist"
                  value={filters.specialist}
                  onChange={(value) => patchFilters({ specialist: value })}
                  items={specialists}
                  active={filters.specialist !== 'all'}
                />
                <FilterSelect
                  label="Outcome"
                  value={filters.outcome}
                  onChange={(value) => patchFilters({ outcome: value })}
                  items={['all', 'win', 'loss', 'breakeven', 'open']}
                  active={filters.outcome !== 'all'}
                />
                <FilterSelect
                  label="Mode"
                  value={filters.mode}
                  onChange={(value) => patchFilters({ mode: value })}
                  items={['all', 'live', 'dry_run']}
                  active={filters.mode !== 'all'}
                />
                <FilterSelect
                  label="Session"
                  value={filters.session}
                  onChange={(value) => patchFilters({ session: value })}
                  items={sessions}
                  active={filters.session !== 'all'}
                />
                <FilterSelect
                  label="Regime"
                  value={filters.regime}
                  onChange={(value) => patchFilters({ regime: value })}
                  items={regimes}
                  active={filters.regime !== 'all'}
                />
                <FilterField label="Start date" active={Boolean(filters.startDate)}>
                  <Input
                    type="date"
                    value={filters.startDate}
                    onChange={(event) => patchFilters({ startDate: event.target.value })}
                    className={filters.startDate ? 'border-sky-400/35 bg-sky-400/10' : ''}
                  />
                </FilterField>
                <FilterField label="End date" active={Boolean(filters.endDate)}>
                  <Input
                    type="date"
                    value={filters.endDate}
                    onChange={(event) => patchFilters({ endDate: event.target.value })}
                    className={filters.endDate ? 'border-sky-400/35 bg-sky-400/10' : ''}
                  />
                </FilterField>
                <div className="flex items-end">
                  <Button
                    variant="ghost"
                    className="w-full"
                    onClick={resetFilters}
                    disabled={!activeFilterCount}
                  >
                    <X className="mr-2 size-4" />
                    Reset filters
                  </Button>
                </div>
              </div>

              {activeFilterCount ? (
                <div className="flex flex-wrap gap-2">
                  {buildActiveFilterBadges(filters).map((label) => (
                    <Badge key={label} variant="outline">
                      {label}
                    </Badge>
                  ))}
                </div>
              ) : null}
            </div>

            <ScrollArea className="h-[30rem] rounded-[24px] border border-white/10 bg-white/[0.02]">
              {filtered.length ? (
                <div className="min-w-[1040px]">
                  <div className="grid grid-cols-[130px_90px_84px_88px_88px_72px_80px_150px_120px_92px_128px_1fr] gap-3 border-b border-white/8 px-4 py-3 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                    <span>Time</span>
                    <span>Symbol</span>
                    <span>Dir</span>
                    <span>Entry</span>
                    <span>Exit</span>
                    <span>Size</span>
                    <span>R</span>
                    <span>Specialist</span>
                    <span>Regime</span>
                    <span>Outcome</span>
                    <span>Slippage</span>
                    <span>Notes</span>
                  </div>
                  {filtered.map((trade) => (
                    <button
                      type="button"
                      key={trade.id}
                      onClick={() => onTradeSelect(trade)}
                      className="grid w-full grid-cols-[130px_90px_84px_88px_88px_72px_80px_150px_120px_92px_128px_1fr] gap-3 border-b border-white/6 px-4 py-3 text-left text-sm transition hover:bg-white/[0.03]"
                    >
                      <span className="text-slate-300">{formatDateTime(trade.entryTime)}</span>
                      <span className="text-white">{trade.symbol}</span>
                      <span className="text-slate-300">{trade.direction}</span>
                      <span className="text-slate-400">{trade.entryPrice.toFixed(1)}</span>
                      <span className="text-slate-400">{trade.exitPrice?.toFixed(1) ?? 'Open'}</span>
                      <span className="text-slate-400">{trade.size}</span>
                      <span className={trade.pnlR >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                        {formatSigned(trade.pnlR)}R
                      </span>
                      <span className="text-slate-300">{trade.specialist}</span>
                      <span className="text-slate-400">{trade.regime}</span>
                      <span>
                        <Badge
                          variant={
                            trade.outcome === 'win'
                              ? 'healthy'
                              : trade.outcome === 'loss'
                                ? 'critical'
                                : 'caution'
                          }
                        >
                          {trade.outcome}
                        </Badge>
                      </span>
                      <span className="text-slate-400">
                        {trade.slippageBps === null ? 'n/a' : `${trade.slippageBps.toFixed(1)} bps`}
                      </span>
                      <span className="truncate text-slate-500">
                        {trade.notes ?? trade.warnings?.[0] ?? `${formatCurrency(trade.pnl)} / ${trade.exitReason}`}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex h-full min-h-[16rem] items-center justify-center px-4 text-center text-sm leading-6 text-slate-500">
                  No executed trades match the current filters. Reset filters to restore the default view.
                </div>
              )}
            </ScrollArea>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function FilterField({
  label,
  active,
  children,
}: {
  label: string
  active?: boolean
  children: ReactNode
}) {
  return (
    <div className="space-y-2">
      <div className={`text-[11px] uppercase tracking-[0.18em] ${active ? 'text-sky-300' : 'text-slate-500'}`}>
        {label}
      </div>
      {children}
    </div>
  )
}

function FilterSelect({
  label,
  value,
  onChange,
  items,
  active,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  items: string[]
  active?: boolean
}) {
  return (
    <FilterField label={label} active={active}>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className={active ? 'border-sky-400/35 bg-sky-400/10' : ''}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {items.map((item) => (
            <SelectItem key={item} value={item}>
              {item}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FilterField>
  )
}

function countActiveFilters(filters: TradeFilters) {
  return Object.entries(filters).filter(([key, value]) => {
    const defaultValue = defaultFilters[key as keyof TradeFilters]
    return value !== defaultValue
  }).length
}

function buildActiveFilterBadges(filters: TradeFilters) {
  const badges: string[] = []
  if (filters.symbol !== 'all') badges.push(`Symbol: ${filters.symbol}`)
  if (filters.specialist !== 'all') badges.push(`Specialist: ${filters.specialist}`)
  if (filters.outcome !== 'all') badges.push(`Outcome: ${filters.outcome}`)
  if (filters.session !== 'all') badges.push(`Session: ${filters.session}`)
  if (filters.regime !== 'all') badges.push(`Regime: ${filters.regime}`)
  if (filters.mode !== 'all') badges.push(`Mode: ${filters.mode}`)
  if (filters.startDate) badges.push(`From: ${filters.startDate}`)
  if (filters.endDate) badges.push(`To: ${filters.endDate}`)
  if (filters.search) badges.push(`Search: ${filters.search}`)
  return badges
}
