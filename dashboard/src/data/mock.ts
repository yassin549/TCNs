import type {
  AllocatorStats,
  DashboardPayload,
  HealthCheck,
  MarketCandle,
  PerformanceSummary,
  SpecialistKey,
  SpecialistStats,
  Trade,
  TradeMarker,
  TradeOutcome,
} from '@/types/trading'

function rng(seed: number) {
  let current = seed
  return () => {
    current = (current * 9301 + 49297) % 233280
    return current / 233280
  }
}

function buildCandles(symbol: string, start: number, base: number): MarketCandle[] {
  const random = rng(symbol === 'US100' ? 17 : 33)
  const candles: MarketCandle[] = []
  let price = base
  for (let index = 0; index < 220; index += 1) {
    const time = new Date(start + index * 60_000).toISOString()
    const drift = (random() - 0.45) * (symbol === 'US100' ? 18 : 4)
    const open = price
    const close = Math.max(10, open + drift)
    const high = Math.max(open, close) + random() * 6
    const low = Math.min(open, close) - random() * 6
    candles.push({
      time,
      open,
      high,
      low,
      close,
      volume: 100 + random() * 240,
    })
    price = close
  }
  return candles
}

function marker(id: string, tradeId: string, time: string, type: TradeMarker['type'], price: number, label: string): TradeMarker {
  return { id, tradeId, time, type, price, label }
}

function buildTrades(candlesBySymbol: Record<string, MarketCandle[]>): Trade[] {
  const templates: Array<{
    symbol: string
    candleIndex: number
    direction: 'long' | 'short'
    specialist: SpecialistKey
    outcome: TradeOutcome
    regime: string
    context: string
    status: 'live' | 'dry_run'
    pnlR: number
  }> = [
    { symbol: 'US100', candleIndex: 34, direction: 'long', specialist: 'long_reversal', outcome: 'win', regime: 'mean reversion', context: 'asia/opening_0_20', status: 'live', pnlR: 1.6 },
    { symbol: 'US100', candleIndex: 72, direction: 'short', specialist: 'short_continuation', outcome: 'loss', regime: 'trend exhaustion', context: 'europe/build_20_40', status: 'live', pnlR: -1 },
    { symbol: 'US100', candleIndex: 109, direction: 'long', specialist: 'long_continuation', outcome: 'breakeven', regime: 'trend persistence', context: 'us/mid_40_60', status: 'dry_run', pnlR: 0.02 },
    { symbol: 'US500', candleIndex: 53, direction: 'short', specialist: 'short_reversal', outcome: 'win', regime: 'volatility spike', context: 'asia/build_20_40', status: 'live', pnlR: 1.2 },
    { symbol: 'US500', candleIndex: 133, direction: 'long', specialist: 'long_reversal', outcome: 'loss', regime: 'failed breakdown', context: 'europe/opening_0_20', status: 'dry_run', pnlR: -0.88 },
    { symbol: 'US500', candleIndex: 176, direction: 'short', specialist: 'short_continuation', outcome: 'open', regime: 'late-session momentum', context: 'us/close_80_100', status: 'live', pnlR: 0.44 },
  ]

  return templates.map((template, index) => {
    const candles = candlesBySymbol[template.symbol]
    const entry = candles[template.candleIndex]
    const exit = candles[Math.min(template.candleIndex + 8, candles.length - 1)]
    const entryPrice = entry.close
    const exitPrice = template.outcome === 'open' ? undefined : exit.close
    const stopPrice = template.direction === 'long' ? entryPrice - 11 : entryPrice + 11
    const targetPrice = template.direction === 'long' ? entryPrice + 18 : entryPrice - 18
    const fillQuality = template.outcome === 'loss' ? 0.72 : 0.91
    const tradeId = `trade-${index + 1}`
    const markers: TradeMarker[] = [
      marker(`${tradeId}-entry`, tradeId, entry.time, template.direction === 'long' ? 'long_entry' : 'short_entry', entryPrice, template.direction === 'long' ? 'Long entry' : 'Short entry'),
    ]

    if (template.outcome !== 'open' && exitPrice) {
      markers.push(
        marker(
          `${tradeId}-exit`,
          tradeId,
          exit.time,
          template.outcome === 'loss'
            ? 'stop_loss'
            : template.outcome === 'breakeven'
              ? 'breakeven'
              : 'take_profit',
          exitPrice,
          template.outcome === 'loss'
            ? 'Stopped'
            : template.outcome === 'breakeven'
              ? 'Breakeven'
              : 'Target hit',
        ),
      )
    }

    return {
      id: tradeId,
      symbol: template.symbol,
      timeframe: '1m',
      specialist: template.specialist,
      direction: template.direction,
      status: template.status,
      outcome: template.outcome,
      entryTime: entry.time,
      exitTime: exitPrice ? exit.time : undefined,
      entryPrice,
      exitPrice,
      stopPrice,
      targetPrice,
      size: template.symbol === 'US100' ? 0.3 : 0.8,
      pnl: template.pnlR * (template.symbol === 'US100' ? 250 : 180),
      pnlR: template.pnlR,
      slippageBps: template.outcome === 'loss' ? 7.3 : 2.4,
      fillQuality,
      session: template.context.split('/')[0],
      regime: template.regime,
      context: template.context,
      entryReason: 'Allocator accepted high-conviction setup with portfolio risk headroom.',
      exitReason:
        template.outcome === 'win'
          ? 'Take-profit reached'
          : template.outcome === 'loss'
            ? 'Stop-loss triggered'
            : template.outcome === 'breakeven'
              ? 'Moved to breakeven after +0.8R'
              : 'Position still open',
      notes: template.outcome === 'open' ? 'Watch fill latency around New York overlap.' : undefined,
      warnings: template.outcome === 'loss' ? ['Diverged from backtest average hold time'] : undefined,
      markers,
    }
  })
}

function buildSpecialists(): SpecialistStats[] {
  return [
    {
      key: 'long_reversal',
      usageCount: 138,
      usagePct: 31,
      acceptedSignals: 42,
      rejectedSignals: 96,
      winRate: 54.1,
      averageR: 0.36,
      rollingPerformance: [0.12, 0.18, 0.15, 0.26, 0.22, 0.35, 0.31],
      health: 'healthy',
      bestContexts: [
        { label: 'asia/opening_0_20', edge: 0.49, winRate: 58.2 },
        { label: 'europe/late_60_80', edge: 0.37, winRate: 53.8 },
      ],
      lastUsed: new Date(Date.now() - 3 * 60_000).toISOString(),
      enabled: true,
      underweight: false,
    },
    {
      key: 'long_continuation',
      usageCount: 81,
      usagePct: 18,
      acceptedSignals: 19,
      rejectedSignals: 62,
      winRate: 42.8,
      averageR: 0.08,
      rollingPerformance: [0.24, 0.19, 0.16, 0.08, 0.04, -0.03, -0.08],
      health: 'caution',
      bestContexts: [
        { label: 'us/close_80_100', edge: 0.28, winRate: 47.3 },
        { label: 'europe/mid_40_60', edge: 0.19, winRate: 45.1 },
      ],
      lastUsed: new Date(Date.now() - 18 * 60_000).toISOString(),
      enabled: true,
      underweight: true,
    },
    {
      key: 'short_continuation',
      usageCount: 149,
      usagePct: 33,
      acceptedSignals: 55,
      rejectedSignals: 94,
      winRate: 49.3,
      averageR: 0.29,
      rollingPerformance: [0.1, 0.12, 0.18, 0.21, 0.27, 0.24, 0.29],
      health: 'healthy',
      bestContexts: [
        { label: 'asia/build_20_40', edge: 0.51, winRate: 54.6 },
        { label: 'us/late_60_80', edge: 0.3, winRate: 49.1 },
      ],
      lastUsed: new Date(Date.now() - 42 * 1000).toISOString(),
      enabled: true,
      underweight: false,
    },
    {
      key: 'short_reversal',
      usageCount: 84,
      usagePct: 18,
      acceptedSignals: 11,
      rejectedSignals: 73,
      winRate: 37.9,
      averageR: -0.06,
      rollingPerformance: [0.16, 0.11, 0.09, 0.03, -0.04, -0.09, -0.12],
      health: 'critical',
      bestContexts: [
        { label: 'asia/build_20_40', edge: 0.22, winRate: 43.8 },
        { label: 'europe/opening_0_20', edge: 0.08, winRate: 39.4 },
      ],
      lastUsed: new Date(Date.now() - 42 * 60_000).toISOString(),
      enabled: false,
      underweight: true,
    },
  ]
}

function buildAllocator(): AllocatorStats {
  return {
    totalCandidates: 428,
    acceptedTrades: 61,
    rejectedTrades: 367,
    currentPortfolioRisk: 0.42,
    maxAllowedRisk: 1,
    concurrentPositions: 1,
    jointAllocationHealthy: true,
    rejectionReasons: [
      { reason: 'Low marginal utility', count: 221 },
      { reason: 'Setup concentration guard', count: 64 },
      { reason: 'Portfolio correlation cap', count: 49 },
      { reason: 'Daily budget exhausted', count: 33 },
    ],
    riskByInstrument: [
      { symbol: 'US100', allocatedRiskPct: 0.25, activeRiskPct: 0.25, signals: 5 },
      { symbol: 'US500', allocatedRiskPct: 0.17, activeRiskPct: 0.17, signals: 4 },
    ],
  }
}

function buildMetrics(trades: Trade[]): PerformanceSummary {
  const realizedTrades = trades.filter((trade) => trade.outcome !== 'open')
  const positiveTrades = realizedTrades.filter((trade) => trade.pnlR > 0)
  const totalPnl = trades.reduce((sum, trade) => sum + trade.pnl, 0)

  return {
    totalPnl,
    dailyPnl: 438,
    weeklyPnl: 1820,
    winRate: (positiveTrades.length / Math.max(1, realizedTrades.length)) * 100,
    profitFactor: 1.34,
    maxDrawdown: 1.19,
    expectancy: 0.46,
    trades: realizedTrades.length,
    averageR: 0.31,
    openRisk: 0.42,
    exposure: 38,
    slippage: 3.2,
    fillQuality: 91,
    rejectedSignals: 367,
    activeSignals: 2,
    equityCurve: Array.from({ length: 24 }, (_, index) => ({
      time: new Date(Date.now() - (24 - index) * 60 * 60 * 1000).toISOString(),
      value: 100000 + index * 420 + (index % 3) * 90 - (index % 5) * 60,
    })),
    pnlDistribution: [
      { bucket: '< -1R', value: 4 },
      { bucket: '-1R', value: 10 },
      { bucket: '0R', value: 8 },
      { bucket: '1R', value: 16 },
      { bucket: '> 1R', value: 6 },
    ],
  }
}

function buildHealthChecks(): HealthCheck[] {
  return [
    {
      id: 'health-1',
      severity: 'critical',
      title: 'Specialist collapse',
      description: 'short_reversal has turned negative over the last 7 accepted samples and is currently disabled.',
      timestamp: new Date(Date.now() - 11 * 60_000).toISOString(),
      action: 'Keep disabled until rolling AP and rolling PnL recover.',
    },
    {
      id: 'health-2',
      severity: 'caution',
      title: 'Repeated rejected signals',
      description: 'Allocator rejected 221 candidates for low utility in the current monitoring window.',
      timestamp: new Date(Date.now() - 6 * 60_000).toISOString(),
      action: 'Review frontier score thresholds and utility normalization.',
    },
    {
      id: 'health-3',
      severity: 'caution',
      title: 'Stale market snapshot',
      description: 'US500 has 55 gap alerts in the rolling snapshot history despite the latest minute being fresh.',
      timestamp: new Date(Date.now() - 3 * 60_000).toISOString(),
      action: 'Inspect broker minute backfill consistency and snapshot updater gaps.',
    },
    {
      id: 'health-4',
      severity: 'healthy',
      title: 'Broker connectivity healthy',
      description: 'Capital.com demo session is authenticated and both configured markets are tradeable.',
      timestamp: new Date(Date.now() - 40 * 1000).toISOString(),
    },
  ]
}

export function generateMockDashboard(): DashboardPayload {
  const start = Date.now() - 219 * 60_000
  const candlesBySymbol = {
    US100: buildCandles('US100', start, 26620),
    US500: buildCandles('US500', start, 7092),
  }
  const trades = buildTrades(candlesBySymbol)
  return {
    session: {
      mode: 'LIVE',
      connectionStatus: 'connected',
      brokerStatus: 'connected',
      health: 'caution',
      lastUpdate: new Date().toISOString(),
      dataFreshnessSeconds: 18,
      marketSession: 'Europe / New York handoff',
      currentSessionLabel: 'Challenge monitoring',
      openPositions: 1,
      activeSpecialists: 3,
      activeSignals: 2,
      rejectedSignals: 367,
      symbols: ['US100', 'US500'],
      timeframes: ['1m', '5m', '15m'],
    },
    metrics: buildMetrics(trades),
    allocator: buildAllocator(),
    specialists: buildSpecialists(),
    healthChecks: buildHealthChecks(),
    trades,
    candlesBySymbol,
  }
}
