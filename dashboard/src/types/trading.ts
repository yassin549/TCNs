export type SystemMode = 'LIVE' | 'DRY RUN' | 'PAUSED' | 'ERROR'
export type ConnectivityState = 'connected' | 'degraded' | 'disconnected'
export type HealthTone = 'healthy' | 'caution' | 'critical'
export type TradeDirection = 'long' | 'short'
export type TradeOutcome = 'win' | 'loss' | 'breakeven' | 'open'
export type TradeMarkerType =
  | 'long_entry'
  | 'short_entry'
  | 'exit'
  | 'stop_loss'
  | 'take_profit'
  | 'breakeven'

export interface LiveSessionMetadata {
  mode: SystemMode
  connectionStatus: ConnectivityState
  brokerStatus: ConnectivityState
  health: HealthTone
  lastUpdate: string
  dataFreshnessSeconds: number
  marketSession: string
  currentSessionLabel: string
  openPositions: number
  activeSpecialists: number
  activeSignals: number
  rejectedSignals: number
  symbols: string[]
  timeframes: string[]
}

export interface MarketCandle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export interface TradeMarker {
  id: string
  tradeId: string
  time: string
  type: TradeMarkerType
  price: number
  label: string
}

export interface Trade {
  id: string
  symbol: string
  timeframe: string
  specialist: SpecialistKey
  direction: TradeDirection
  status: 'live' | 'dry_run'
  outcome: TradeOutcome
  entryTime: string
  exitTime?: string
  entryPrice: number
  exitPrice?: number
  stopPrice: number
  targetPrice: number
  size: number
  pnl: number
  pnlR: number
  slippageBps: number | null
  fillQuality: number | null
  session: string
  regime: string
  context: string
  entryReason: string
  exitReason: string
  notes?: string
  warnings?: string[]
  markers: TradeMarker[]
}

export type SpecialistKey =
  | 'long_reversal'
  | 'long_continuation'
  | 'short_continuation'
  | 'short_reversal'

export interface SpecialistContextSlice {
  label: string
  edge: number
  winRate: number | null
}

export interface SpecialistStats {
  key: SpecialistKey
  usageCount: number
  usagePct: number
  acceptedSignals: number
  rejectedSignals: number
  winRate: number | null
  averageR: number | null
  rollingPerformance: number[]
  health: HealthTone
  bestContexts: SpecialistContextSlice[]
  lastUsed: string
  enabled: boolean
  underweight: boolean
}

export interface AllocatorRejectionReason {
  reason: string
  count: number
}

export interface InstrumentRiskAllocation {
  symbol: string
  allocatedRiskPct: number
  activeRiskPct: number
  signals: number
}

export interface AllocatorStats {
  totalCandidates: number
  acceptedTrades: number
  rejectedTrades: number
  currentPortfolioRisk: number
  maxAllowedRisk: number
  concurrentPositions: number
  jointAllocationHealthy: boolean
  rejectionReasons: AllocatorRejectionReason[]
  riskByInstrument: InstrumentRiskAllocation[]
}

export interface HealthCheck {
  id: string
  severity: HealthTone
  title: string
  description: string
  timestamp: string
  action?: string
}

export interface PerformanceMetric {
  label: string
  value: number
  delta?: number
  unit?: 'currency' | 'percent' | 'ratio' | 'count' | 'r'
}

export interface PerformanceSummary {
  totalPnl: number
  dailyPnl: number
  weeklyPnl: number
  winRate: number | null
  profitFactor: number | null
  maxDrawdown: number
  expectancy: number | null
  trades: number
  averageR: number | null
  openRisk: number
  exposure: number
  slippage: number | null
  fillQuality: number | null
  rejectedSignals: number
  activeSignals: number
  equityCurve: Array<{ time: string; value: number }>
  pnlDistribution: Array<{ bucket: string; value: number }>
}

export interface DashboardPayload {
  session: LiveSessionMetadata
  metrics: PerformanceSummary
  allocator: AllocatorStats
  specialists: SpecialistStats[]
  healthChecks: HealthCheck[]
  trades: Trade[]
  candlesBySymbol: Record<string, MarketCandle[]>
}

export interface TradeFilters {
  symbol: string
  specialist: string
  outcome: string
  session: string
  regime: string
  mode: string
  startDate: string
  endDate: string
  search: string
}
