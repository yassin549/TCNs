import { useEffect, useMemo, useState } from 'react'

import { generateMockDashboard } from '@/data/mock'
import type { TradingMonitorApi } from '@/services/api'
import type { DashboardPayload } from '@/types/trading'

class MockTradingMonitorApi implements TradingMonitorApi {
  async getDashboard() {
    return generateMockDashboard()
  }
}

class LocalSnapshotApi implements TradingMonitorApi {
  async getDashboard() {
    const response = await fetch(`/dashboard-data.json?ts=${Date.now()}`, {
      cache: 'no-store',
    })
    if (!response.ok) {
      throw new Error(`Local snapshot unavailable: ${response.status}`)
    }
    return response.json()
  }
}

async function fetchDashboard(baseUrl: string): Promise<DashboardPayload> {
  const [status, metrics, trades, specialists, health] = await Promise.all([
    fetch(`${baseUrl}/api/status`).then((response) => response.json()),
    fetch(`${baseUrl}/api/metrics`).then((response) => response.json()),
    fetch(`${baseUrl}/api/trades`).then((response) => response.json()),
    fetch(`${baseUrl}/api/specialists`).then((response) => response.json()),
    fetch(`${baseUrl}/api/health`).then((response) => response.json()),
  ])

  return {
    session: status.session,
    metrics,
    allocator: metrics.allocator,
    trades,
    specialists,
    healthChecks: health,
    candlesBySymbol: status.candlesBySymbol,
  }
}

export function useDashboardData(refreshMs = 15_000) {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined
  const allowMockFallback = import.meta.env.VITE_ENABLE_MOCK_DASHBOARD === 'true'
  const [data, setData] = useState<DashboardPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [source, setSource] = useState<'api' | 'local' | 'mock'>('local')

  const client = useMemo<TradingMonitorApi>(() => {
    if (apiBaseUrl) {
      return {
        getDashboard: () => fetchDashboard(apiBaseUrl),
      }
    }
    return new LocalSnapshotApi()
  }, [apiBaseUrl])

  useEffect(() => {
    let active = true

    const load = async (isInitial = false) => {
      if (isInitial) {
        setLoading(true)
      }
      try {
        const payload = await client.getDashboard()
        if (!active) return
        setData(payload)
        setError(null)
        setSource(apiBaseUrl ? 'api' : 'local')
      } catch (loadError) {
        if (!active) return
        if (!apiBaseUrl && allowMockFallback) {
          const payload = await new MockTradingMonitorApi().getDashboard()
          if (!active) return
          setData(payload)
          setError(null)
          setSource('mock')
          return
        }
        setData(null)
        setError(loadError instanceof Error ? loadError.message : 'Unknown data error')
      } finally {
        if (isInitial && active) {
          setLoading(false)
        }
      }
    }

    void load(true)
    const timer = window.setInterval(() => {
      void load(false)
    }, refreshMs)

    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [allowMockFallback, apiBaseUrl, client, refreshMs])

  return { data, loading, error, source }
}
