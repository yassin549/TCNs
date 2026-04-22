import type { DashboardPayload } from '@/types/trading'

export interface TradingMonitorApi {
  getDashboard(): Promise<DashboardPayload>
  subscribe?(onMessage: (payload: DashboardPayload) => void): () => void
}

export const API_ROUTES = {
  status: '/api/status',
  metrics: '/api/metrics',
  trades: '/api/trades',
  specialists: '/api/specialists',
  health: '/api/health',
  ohlcv: '/api/ohlcv?symbol=',
  websocket: '/ws/live',
}

