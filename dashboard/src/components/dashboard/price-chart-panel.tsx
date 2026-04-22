import { type ReactNode, useEffect, useMemo, useRef, useState } from 'react'

import {
  CandlestickSeries,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
  createChart,
  createSeriesMarkers,
} from 'lightweight-charts'
import { CandlestickChart, ScanSearch } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatCurrency, formatDateTime, formatSigned } from '@/lib/format'
import type { MarketCandle, Trade, TradeMarker } from '@/types/trading'

type MarkerLookup = {
  trade: Trade
  marker: TradeMarker
}

export function PriceChartPanel({
  symbol,
  symbols,
  timeframe,
  timeframes,
  candles,
  trades,
  selectedTradeId,
  onSelectedTradeChange,
  onSymbolChange,
  onTimeframeChange,
  onMarkerSelect,
}: {
  symbol: string
  symbols: string[]
  timeframe: string
  timeframes: string[]
  candles: MarketCandle[]
  trades: Trade[]
  selectedTradeId?: string
  onSelectedTradeChange: (tradeId: string) => void
  onSymbolChange: (value: string) => void
  onTimeframeChange: (value: string) => void
  onMarkerSelect: (trade: Trade) => void
}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const markerLookupRef = useRef<Map<string, MarkerLookup>>(new Map())
  const hasFitContentRef = useRef(false)
  const [hoveredTrade, setHoveredTrade] = useState<Trade | null>(null)

  const chartTrades = useMemo(() => trades.filter((trade) => trade.symbol === symbol), [symbol, trades])
  const selectedTrade = useMemo(
    () => chartTrades.find((trade) => trade.id === selectedTradeId) ?? null,
    [chartTrades, selectedTradeId],
  )
  const visibleHoveredTrade = hoveredTrade?.symbol === symbol ? hoveredTrade : null
  const focusTrade = visibleHoveredTrade ?? selectedTrade ?? chartTrades[0] ?? null

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      crosshair: {
        vertLine: { color: 'rgba(148,163,184,0.28)', labelBackgroundColor: '#101722' },
        horzLine: { color: 'rgba(148,163,184,0.18)', labelBackgroundColor: '#101722' },
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.08)',
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.08)',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: true,
      handleScale: true,
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#34d399',
      downColor: '#fb7185',
      borderVisible: false,
      wickUpColor: '#34d399',
      wickDownColor: '#fb7185',
      priceLineVisible: false,
    })

    const markersPlugin = createSeriesMarkers(series, [], {
      autoScale: true,
      zOrder: 'top',
    })

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      const lookup = markerLookupRef.current.get(String(param.hoveredObjectId ?? ''))
      setHoveredTrade(lookup?.trade ?? null)
    }

    const handleChartClick = (param: MouseEventParams<Time>) => {
      const lookup = markerLookupRef.current.get(String(param.hoveredObjectId ?? ''))
      if (!lookup) return
      onSelectedTradeChange(lookup.trade.id)
      onMarkerSelect(lookup.trade)
    }

    chart.subscribeCrosshairMove(handleCrosshairMove)
    chart.subscribeClick(handleChartClick)

    chartRef.current = chart
    seriesRef.current = series
    markersPluginRef.current = markersPlugin

    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove)
      chart.unsubscribeClick(handleChartClick)
      markersPlugin.detach()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
      markersPluginRef.current = null
      hasFitContentRef.current = false
    }
  }, [onMarkerSelect, onSelectedTradeChange])

  useEffect(() => {
    if (!seriesRef.current || !markersPluginRef.current || !chartRef.current) return

    seriesRef.current.setData(
      candles.map((candle) => ({
        time: Math.floor(new Date(candle.time).getTime() / 1000) as Time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    )

    const markerLookup = new Map<string, MarkerLookup>()
    const markers = chartTrades
      .flatMap((trade) =>
        trade.markers.map((marker) => {
          const id = `${trade.id}:${marker.id}`
          markerLookup.set(id, { trade, marker })
          return buildSeriesMarker(marker, id)
        }),
      )
      .sort((left, right) => Number(left.time) - Number(right.time)) as SeriesMarker<Time>[]

    markersPluginRef.current.setMarkers(markers)
    markerLookupRef.current = markerLookup

    if (!hasFitContentRef.current && candles.length) {
      chartRef.current.timeScale().fitContent()
      hasFitContentRef.current = true
    }
  }, [candles, chartTrades])

  useEffect(() => {
    hasFitContentRef.current = false
  }, [symbol, timeframe])

  useEffect(() => {
    if (!selectedTradeId || !chartRef.current) return
    const trade = chartTrades.find((item) => item.id === selectedTradeId)
    if (!trade) return
    const tradeTime = Math.floor(new Date(trade.entryTime).getTime() / 1000)
    chartRef.current.timeScale().setVisibleRange({
      from: (tradeTime - 20 * 60) as Time,
      to: (tradeTime + 40 * 60) as Time,
    })
  }, [chartTrades, selectedTradeId])

  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden">
      <CardHeader className="border-b border-white/6 pb-6">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <CandlestickChart className="size-4 text-sky-300" />
            Market activity
          </CardTitle>
          <CardDescription className="mt-1">
            The chart stays primary. Hover previews and one-click marker selection keep details nearby without burying price action.
          </CardDescription>
        </div>
        <div className="grid w-full gap-3 sm:grid-cols-2 xl:w-auto xl:min-w-[280px]">
          <ControlField label="Symbol">
            <Select value={symbol} onValueChange={onSymbolChange}>
              <SelectTrigger>
                <SelectValue placeholder="Symbol" />
              </SelectTrigger>
              <SelectContent>
                {symbols.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </ControlField>
          <ControlField label="Timeframe">
            <Select value={timeframe} onValueChange={onTimeframeChange}>
              <SelectTrigger>
                <SelectValue placeholder="Timeframe" />
              </SelectTrigger>
              <SelectContent>
                {timeframes.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </ControlField>
        </div>
      </CardHeader>
      <CardContent className="grid min-h-0 flex-1 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_320px] lg:p-6">
        <div className="space-y-4">
          <div className="min-h-[28rem] overflow-hidden rounded-[22px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.12),transparent_28%),rgba(255,255,255,0.02)] p-3 md:h-[34rem] xl:h-[40rem]">
            <div ref={containerRef} className="h-full w-full" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <MarkerLegendItem label="Long entry" tone="bg-sky-400" />
            <MarkerLegendItem label="Short entry" tone="bg-orange-400" />
            <MarkerLegendItem label="Take profit" tone="bg-emerald-400" />
            <MarkerLegendItem label="Stop loss" tone="bg-rose-400" />
            <MarkerLegendItem label="Breakeven / exit" tone="bg-amber-300" />
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-4">
          <div className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                  {visibleHoveredTrade ? 'Hover preview' : selectedTrade ? 'Selected trade' : 'Focus trade'}
                </div>
                <div className="mt-1 text-sm text-slate-400">
                  {focusTrade ? 'Quick context without leaving the chart.' : 'Hover a marker or select a trade from the list.'}
                </div>
              </div>
              <Badge variant="outline">{chartTrades.length} trades</Badge>
            </div>

            {focusTrade ? (
              <div className="mt-4 space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-lg font-semibold text-white">
                    {focusTrade.symbol} {focusTrade.direction === 'long' ? 'long' : 'short'}
                  </div>
                  <Badge
                    variant={
                      focusTrade.outcome === 'win'
                        ? 'healthy'
                        : focusTrade.outcome === 'loss'
                          ? 'critical'
                          : 'caution'
                    }
                  >
                    {focusTrade.outcome}
                  </Badge>
                  <Badge variant="outline">{focusTrade.specialist}</Badge>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <MiniStat label="Entry" value={formatDateTime(focusTrade.entryTime)} />
                  <MiniStat label="PnL" value={`${formatCurrency(focusTrade.pnl)} / ${formatSigned(focusTrade.pnlR)}R`} />
                </div>
                <Button variant="primary" className="w-full" onClick={() => onMarkerSelect(focusTrade)}>
                  Open trade details
                </Button>
              </div>
            ) : (
              <div className="mt-4 rounded-[18px] border border-white/8 bg-slate-950/30 p-4 text-sm text-slate-500">
                No executed trades are available for the selected symbol yet.
              </div>
            )}
          </div>

          <div className="flex min-h-0 flex-1 flex-col rounded-[22px] border border-white/10 bg-white/[0.03]">
            <div className="flex items-center justify-between gap-3 border-b border-white/6 px-4 py-4">
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <ScanSearch className="size-4 text-slate-300" />
                  Visible trades
                </div>
                <div className="mt-1 text-sm text-slate-400">Select a row to center the chart. Click the button above for the drawer.</div>
              </div>
            </div>
            <ScrollArea className="min-h-[18rem] flex-1 px-3 pb-3">
              {chartTrades.length ? (
                <div className="space-y-2 pt-3">
                  {chartTrades.map((trade) => (
                    <button
                      key={trade.id}
                      type="button"
                      onClick={() => onSelectedTradeChange(trade.id)}
                      className={`w-full rounded-[18px] border p-3 text-left transition ${
                        selectedTradeId === trade.id
                          ? 'border-sky-400/45 bg-sky-400/10'
                          : 'border-white/6 bg-white/[0.02] hover:bg-white/[0.05]'
                      }`}
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <div className="font-medium text-white">
                          {trade.direction === 'long' ? 'Long' : 'Short'} / {trade.specialist}
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
                      <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                        <span>{formatDateTime(trade.entryTime)}</span>
                        <span className="text-right">{formatCurrency(trade.pnl)}</span>
                        <span>{trade.context}</span>
                        <span className="text-right">{formatSigned(trade.pnlR)}R</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex h-full min-h-[18rem] items-center justify-center px-4 text-center text-sm leading-6 text-slate-500">
                  No executed trades are available in the current local paper or live state yet.
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ControlField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      {children}
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-white/8 bg-slate-950/35 p-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-sm text-white">{value}</div>
    </div>
  )
}

function MarkerLegendItem({ label, tone }: { label: string; tone: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[18px] border border-white/8 bg-white/[0.03] px-3 py-2.5 text-sm text-slate-300">
      <span className={`size-2.5 rounded-full ${tone}`} />
      {label}
    </div>
  )
}

function buildSeriesMarker(marker: TradeMarker, id: string): SeriesMarker<Time> {
  const time = Math.floor(new Date(marker.time).getTime() / 1000) as Time

  switch (marker.type) {
    case 'long_entry':
      return {
        id,
        time,
        position: 'belowBar',
        color: '#38bdf8',
        shape: 'arrowUp',
        text: 'LONG',
      }
    case 'short_entry':
      return {
        id,
        time,
        position: 'aboveBar',
        color: '#f97316',
        shape: 'arrowDown',
        text: 'SHORT',
      }
    case 'take_profit':
      return {
        id,
        time,
        position: 'atPriceTop',
        price: marker.price,
        color: '#34d399',
        shape: 'circle',
        text: 'TP',
      }
    case 'stop_loss':
      return {
        id,
        time,
        position: 'atPriceBottom',
        price: marker.price,
        color: '#fb7185',
        shape: 'circle',
        text: 'SL',
      }
    case 'breakeven':
      return {
        id,
        time,
        position: 'atPriceMiddle',
        price: marker.price,
        color: '#fbbf24',
        shape: 'square',
        text: 'BE',
      }
    case 'exit':
    default:
      return {
        id,
        time,
        position: 'atPriceMiddle',
        price: marker.price,
        color: '#c084fc',
        shape: 'circle',
        text: 'EXIT',
      }
  }
}
