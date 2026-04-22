import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const dashboardDir = process.cwd()
const repoRoot = path.resolve(dashboardDir, '..')
const outputPath = path.join(dashboardDir, 'public', 'dashboard-data.json')

const instruments = ['US100', 'US500']

function readJson(filePath, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch {
    return fallback
  }
}

function readJsonLines(filePath) {
  if (!fs.existsSync(filePath)) return []
  return fs
    .readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line)
      } catch {
        return null
      }
    })
    .filter(Boolean)
}

function readEnv(filePath) {
  if (!fs.existsSync(filePath)) return {}
  return Object.fromEntries(
    fs
      .readFileSync(filePath, 'utf8')
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#') && line.includes('='))
      .map((line) => {
        const idx = line.indexOf('=')
        return [line.slice(0, idx), line.slice(idx + 1)]
      }),
  )
}

function readCsvGz(filePath, limit = 240) {
  if (!fs.existsSync(filePath)) return []
  const content = zlib.gunzipSync(fs.readFileSync(filePath)).toString('utf8').trim()
  const lines = content.split(/\r?\n/)
  const header = lines[0].split(',')
  const rows = lines.slice(Math.max(1, lines.length - limit))
  return rows.map((line) => {
    const values = line.split(',')
    return Object.fromEntries(header.map((key, index) => [key, values[index] ?? '']))
  })
}

function toNumber(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function average(values) {
  return values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null
}

function parseTime(value) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function marketSessionForTime(iso) {
  const date = parseTime(iso) ?? new Date()
  const hour = date.getUTCHours()
  if (hour >= 23 || hour < 7) return 'asia'
  if (hour < 13) return 'europe'
  if (hour < 21) return 'us'
  return 'close'
}

function sessionPhase(candidate) {
  const barIndex = toNumber(candidate?.bar_index_in_segment, 0)
  const remaining = toNumber(candidate?.bars_remaining_in_segment, 0)
  const total = Math.max(1, barIndex + remaining + 1)
  const progress = barIndex / total
  if (progress < 0.2) return 'opening_0_20'
  if (progress < 0.4) return 'build_20_40'
  if (progress < 0.6) return 'mid_40_60'
  if (progress < 0.8) return 'late_60_80'
  return 'close_80_100'
}

function contextForDecision(decision) {
  const timestamp = decision?.candidate?.timestamp || decision?.timestamp_utc
  return `${marketSessionForTime(timestamp)}|${sessionPhase(decision?.candidate ?? {})}`
}

function buildTradeFromPaper(entry, fallbackStatus = 'dry_run') {
  const candidate = entry.candidate ?? {}
  const orderPlan = entry.order_plan ?? {}
  const resolution = entry.resolution
  const pnlR = toNumber(resolution?.pnl_r, 0)
  const outcome =
    !resolution
      ? 'open'
      : (resolution.exit_reason === 'breakeven' || Math.abs(pnlR) < 0.05)
        ? 'breakeven'
        : pnlR > 0
          ? 'win'
          : 'loss'
  const direction = String(orderPlan.direction || '').toUpperCase() === 'SELL' ? 'short' : 'long'
  const entryTime = String(orderPlan.signal_timestamp || candidate.timestamp || '')
  const exitTime = resolution?.exit_timestamp ? String(resolution.exit_timestamp) : undefined
  const tradeId = `${entry.instrument_id}-${entryTime}`
  const entryPrice = toNumber(orderPlan.entry_price ?? candidate.close)
  const exitPrice = resolution ? toNumber(resolution.exit_price) : undefined
  const stopPrice = toNumber(orderPlan.stop_price ?? 0)
  const targetPrice = toNumber(orderPlan.target_price ?? 0)
  const status = fallbackStatus
  return {
    id: tradeId,
    symbol: String(entry.instrument_id || candidate.instrument_id || 'UNKNOWN'),
    timeframe: '1m',
    specialist: String(candidate.chosen_setup || orderPlan.chosen_setup || 'unknown'),
    direction,
    status,
    outcome,
    entryTime,
    exitTime,
    entryPrice,
    exitPrice,
    stopPrice,
    targetPrice,
    size: toNumber(orderPlan.size, 0),
    pnl: toNumber(resolution?.pnl_cash, 0),
    pnlR,
    slippageBps: null,
    fillQuality: null,
    session: marketSessionForTime(entryTime),
    regime: contextForDecision({ candidate }),
    context: contextForDecision({ candidate }),
    entryReason: `Frontier ${toNumber(candidate.predicted_frontier_score, 0).toFixed(3)} / prob ${toNumber(candidate.probability, 0).toFixed(3)}`,
    exitReason: resolution ? String(resolution.exit_reason || 'closed') : 'Position open',
    notes: undefined,
    warnings: [],
    markers: [
      {
        id: `${tradeId}-entry`,
        tradeId,
        time: entryTime,
        type: direction === 'long' ? 'long_entry' : 'short_entry',
        price: entryPrice,
        label: direction === 'long' ? 'Long entry' : 'Short entry',
      },
      ...(resolution && exitTime
        ? [
            {
              id: `${tradeId}-exit`,
              tradeId,
              time: exitTime,
              type:
                outcome === 'loss'
                  ? 'stop_loss'
                  : outcome === 'breakeven'
                    ? 'breakeven'
                    : 'take_profit',
              price: toNumber(resolution.exit_price, entryPrice),
              label: outcome === 'loss' ? 'Stop' : outcome === 'breakeven' ? 'Breakeven' : 'Target',
            },
          ]
        : []),
    ],
  }
}

function computeDrawdown(series) {
  let peak = Number.NEGATIVE_INFINITY
  let worst = 0
  for (const point of series) {
    peak = Math.max(peak, point.value)
    worst = Math.min(worst, point.value - peak)
  }
  return Math.abs(worst)
}

function buildDashboardSnapshot() {
  const env = readEnv(path.join(repoRoot, '.env'))
  const artifactDir = env.CAPITAL_ARTIFACTS_DIR_US100
    ? path.join(repoRoot, env.CAPITAL_ARTIFACTS_DIR_US100)
    : null
  const artifactAnalysis = artifactDir
    ? readJson(path.join(artifactDir, 'analysis_report.json'), {})
    : {}
  const serverState = readJson(path.join(repoRoot, 'artifacts', 'live_capital', '_server_state.json'), {})
  const paperState = readJson(path.join(repoRoot, 'artifacts', 'live_capital', '_paper_state.json'), {
    open_positions: [],
    closed_trades: [],
  })
  const metricsHistory = readJsonLines(path.join(repoRoot, 'artifacts', 'live_capital', 'server_metrics.jsonl'))
  const latestMetrics = metricsHistory.at(-1) ?? {}

  const decisionLogsByInstrument = Object.fromEntries(
    instruments.map((instrument) => [
      instrument,
      readJsonLines(path.join(repoRoot, 'artifacts', 'live_capital', instrument.toLowerCase(), 'live_decisions.jsonl')),
    ]),
  )
  const allDecisions = instruments.flatMap((instrument) => decisionLogsByInstrument[instrument])

  const candlesBySymbol = Object.fromEntries(
    instruments.map((instrument) => {
      const csvRows = readCsvGz(path.join(repoRoot, 'artifacts', 'live_snapshots', `${instrument.toLowerCase()}_live_snapshot.csv.gz`))
      return [
        instrument,
        csvRows.map((row) => ({
          time: row.timestamp,
          open: toNumber(row.open),
          high: toNumber(row.high),
          low: toNumber(row.low),
          close: toNumber(row.close),
        })),
      ]
    }),
  )

  const paperTrades = [
    ...(paperState.closed_trades ?? []).map((entry) => buildTradeFromPaper(entry, 'dry_run')),
    ...(paperState.open_positions ?? []).map((entry) =>
      buildTradeFromPaper(
        {
          instrument_id: entry.instrument_id,
          candidate: entry.candidate,
          order_plan: entry.order_plan,
        },
        'dry_run',
      ),
    ),
  ].sort((a, b) => new Date(b.entryTime).getTime() - new Date(a.entryTime).getTime())

  const closedTrades = paperTrades.filter((trade) => trade.outcome !== 'open')
  const now = new Date()
  const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  const dailyPnl = closedTrades
    .filter((trade) => parseTime(trade.exitTime ?? trade.entryTime) >= dayAgo)
    .reduce((sum, trade) => sum + trade.pnl, 0)
  const weeklyPnl = closedTrades
    .filter((trade) => parseTime(trade.exitTime ?? trade.entryTime) >= weekAgo)
    .reduce((sum, trade) => sum + trade.pnl, 0)
  const totalPnl = closedTrades.reduce((sum, trade) => sum + trade.pnl, 0)
  const wins = closedTrades.filter((trade) => trade.pnlR > 0)
  const losses = closedTrades.filter((trade) => trade.pnlR < 0)
  const grossWins = wins.reduce((sum, trade) => sum + trade.pnlR, 0)
  const grossLosses = Math.abs(losses.reduce((sum, trade) => sum + trade.pnlR, 0))
  const winRate = closedTrades.length ? (wins.length / closedTrades.length) * 100 : null
  const expectancy = closedTrades.length
    ? closedTrades.reduce((sum, trade) => sum + trade.pnlR, 0) / closedTrades.length
    : null
  const averageR = expectancy
  const measuredSlippages = closedTrades
    .map((trade) => trade.slippageBps)
    .filter((value) => value !== null)
  const measuredFillQuality = closedTrades
    .map((trade) => trade.fillQuality)
    .filter((value) => value !== null)
  const slippage = average(measuredSlippages)
  const fillQuality = average(measuredFillQuality)

  const equityCurve = metricsHistory.slice(-120).map((item) => ({
    time: item.timestamp_utc,
    value: toNumber(item.account_balance, toNumber(serverState.prop_starting_balance, 0)),
  }))
  const maxDrawdownCash = computeDrawdown(equityCurve)
  const startingBalance = toNumber(latestMetrics.starting_balance, toNumber(serverState.prop_starting_balance, 1))
  const maxDrawdownPct = startingBalance > 0 ? (maxDrawdownCash / startingBalance) * 100 : 0
  const maxAllowedRisk = toNumber(env.CAPITAL_MAX_PORTFOLIO_RISK_PCT, 1)

  const rejectedSignalsTotal = allDecisions.filter((item) => item.mode === 'hold').length
  const acceptedSignalsTotal = allDecisions.filter((item) => item.mode !== 'hold').length

  const buckets = {
    '< -1R': 0,
    '-1R to 0R': 0,
    '0R': 0,
    '0R to 1R': 0,
    '> 1R': 0,
  }
  for (const trade of closedTrades) {
    if (trade.pnlR < -1) buckets['< -1R'] += 1
    else if (trade.pnlR < 0) buckets['-1R to 0R'] += 1
    else if (Math.abs(trade.pnlR) < 0.05) buckets['0R'] += 1
    else if (trade.pnlR <= 1) buckets['0R to 1R'] += 1
    else buckets['> 1R'] += 1
  }

  const specialists = ['long_reversal', 'long_continuation', 'short_continuation', 'short_reversal'].map((setup) => {
    const setupDecisions = allDecisions.filter((item) => item.candidate?.chosen_setup === setup)
    const setupTrades = paperTrades.filter((trade) => trade.specialist === setup)
    const closedSetupTrades = setupTrades.filter((trade) => trade.outcome !== 'open')
    const recentFrontier = setupDecisions.slice(-12).map((item) => toNumber(item.candidate?.predicted_frontier_score, 0))
    const avgRecentFrontier = recentFrontier.length
      ? recentFrontier.reduce((sum, value) => sum + value, 0) / recentFrontier.length
      : 0
    const tradeContexts = closedSetupTrades.reduce((acc, trade) => {
      const bucket = acc[trade.context] ?? { trades: 0, wins: 0 }
      bucket.trades += 1
      if (trade.pnlR > 0) bucket.wins += 1
      acc[trade.context] = bucket
      return acc
    }, {})
    const contexts = Object.values(
      setupDecisions.reduce((acc, item) => {
        const context = contextForDecision(item)
        const bucket = acc[context] ?? { label: context, count: 0, frontier: 0 }
        bucket.count += 1
        bucket.frontier += toNumber(item.candidate?.predicted_frontier_score, 0)
        acc[context] = bucket
        return acc
      }, {}),
    )
      .sort((a, b) => b.frontier / Math.max(1, b.count) - a.frontier / Math.max(1, a.count))
      .slice(0, 2)
      .map((item) => ({
        label: item.label,
        edge: item.frontier / Math.max(1, item.count),
        winRate: tradeContexts[item.label]?.trades
          ? (tradeContexts[item.label].wins / tradeContexts[item.label].trades) * 100
          : null,
      }))

    const avgR =
      closedSetupTrades.length > 0
        ? closedSetupTrades.reduce((sum, trade) => sum + trade.pnlR, 0) / closedSetupTrades.length
        : null
    const health =
      setupDecisions.length === 0
        ? 'caution'
        : closedSetupTrades.length >= 3 && avgR !== null && avgR < 0
        ? 'critical'
        : setupDecisions.length >= 6 && setupDecisions.every((item) => item.mode === 'hold')
          ? avgRecentFrontier < -1 ? 'critical' : 'caution'
          : avgRecentFrontier < -0.5
            ? 'caution'
            : 'healthy'

    return {
      key: setup,
      usageCount: setupDecisions.length,
      usagePct: allDecisions.length ? (setupDecisions.length / allDecisions.length) * 100 : 0,
      acceptedSignals: setupDecisions.filter((item) => item.mode !== 'hold').length,
      rejectedSignals: setupDecisions.filter((item) => item.mode === 'hold').length,
      winRate: closedSetupTrades.length ? (closedSetupTrades.filter((trade) => trade.pnlR > 0).length / closedSetupTrades.length) * 100 : null,
      averageR: avgR,
      rollingPerformance: closedSetupTrades.slice(-7).map((trade) => trade.pnlR),
      health,
      bestContexts: contexts,
      lastUsed: setupDecisions.at(-1)?.timestamp_utc ?? latestMetrics.timestamp_utc ?? new Date().toISOString(),
      enabled: health !== 'critical',
      underweight: health !== 'healthy' || setupDecisions.filter((item) => item.mode !== 'hold').length === 0,
    }
  })

  const latestResults = latestMetrics.results ?? []
  const latestSignals = latestResults.filter((result) => result.candidate?.timestamp)
  const latestActionableSignals = latestSignals.filter((result) => result.mode && result.mode !== 'hold')
  const latestRejectedSignals = latestSignals.filter((result) => result.mode === 'hold')
  const latestOpenRisk = Object.values(latestMetrics.instrument_status ?? {}).reduce(
    (sum, item) => sum + toNumber(item.applied_risk_pct, 0),
    0,
  )

  const riskByInstrument = instruments.map((instrument) => {
    const status = latestMetrics.instrument_status?.[instrument] ?? {}
    return {
      symbol: instrument,
      allocatedRiskPct: toNumber(status.applied_risk_pct, 0),
      activeRiskPct: status.mode && status.mode !== 'hold' ? toNumber(status.applied_risk_pct, 0) : 0,
      signals: decisionLogsByInstrument[instrument].length,
    }
  })

  const rejectionReasons = Object.entries(
    allDecisions.reduce((acc, item) => {
      const reason = String(item.reason || (item.mode === 'hold' ? 'hold' : 'accepted'))
      if (reason === 'accepted') return acc
      acc[reason] = (acc[reason] ?? 0) + 1
      return acc
    }, {}),
  )
    .map(([reason, count]) => ({ reason, count }))
    .sort((a, b) => b.count - a.count)

  const contractWarnings = instruments
    .map((instrument) => {
      const pointValue = env[`CAPITAL_POINT_VALUE_${instrument}`]
      const minSize = env[`CAPITAL_MIN_SIZE_${instrument}`]
      const sizeStep = env[`CAPITAL_SIZE_STEP_${instrument}`]
      return !pointValue || !minSize || !sizeStep ? instrument : null
    })
    .filter(Boolean)

  const baselinePositiveRate = toNumber(artifactAnalysis?.frontier_score_summary?.positive_rate, 0)
  const liveAcceptanceRate = allDecisions.length ? acceptedSignalsTotal / allDecisions.length : 0
  const healthChecks = []

  if (contractWarnings.length) {
    healthChecks.push({
      id: 'missing-calibration',
      severity: 'critical',
      title: 'Missing contract calibration',
      description: `Missing point value or size settings for ${contractWarnings.join(', ')}.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Set per-instrument Capital.com contract sizing fields before live execution.',
    })
  }

  for (const instrument of instruments) {
    const snapshot = latestMetrics.snapshot_status_by_instrument?.[instrument]
    if (!snapshot) continue
    if (toNumber(snapshot.latest_age_seconds, 0) > 60 || toNumber(snapshot.snapshot_latest_age_seconds, 0) > 60) {
      healthChecks.push({
        id: `lag-${instrument}`,
        severity: 'critical',
        title: `Data lag on ${instrument}`,
        description: `Latest ${instrument} snapshot is ${toNumber(snapshot.latest_age_seconds, 0).toFixed(0)} seconds old.`,
        timestamp: snapshot.last_update_time_utc ?? latestMetrics.timestamp_utc,
        action: 'Check broker connectivity and snapshot updater polling.',
      })
    } else if ((snapshot.missing_data_alerts ?? []).length > 0) {
      healthChecks.push({
        id: `stale-${instrument}`,
        severity: 'caution',
        title: `${instrument} snapshot gaps detected`,
        description: `${(snapshot.missing_data_alerts ?? []).length} missing-data alerts recorded in the rolling snapshot history.`,
        timestamp: snapshot.last_update_time_utc ?? latestMetrics.timestamp_utc,
        action: 'Inspect historical minute backfill quality for this instrument.',
      })
    }
  }

  if (latestMetrics.open_positions_total === 0 && latestActionableSignals.length > 0) {
    healthChecks.push({
      id: 'signals-without-positions',
      severity: 'caution',
      title: 'No open positions while signals exist',
      description: `${latestActionableSignals.length} actionable signals were processed but no positions are open.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Confirm whether the manager is intentionally filtering all current opportunities.',
    })
  }

  const last20Rejected = allDecisions.slice(-20).filter((item) => item.mode === 'hold').length
  if (last20Rejected >= 10) {
    healthChecks.push({
      id: 'repeated-rejections',
      severity: 'caution',
      title: 'Repeated rejected signals',
      description: `${last20Rejected} of the last ${Math.min(20, allDecisions.length)} decisions were rejected.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Review frontier-score and allocator thresholds against current live conditions.',
    })
  }

  if (closedTrades.length >= 10 && losses.length === 0) {
    healthChecks.push({
      id: 'suspicious-no-losses',
      severity: 'critical',
      title: 'No losses in suspicious sample',
      description: `Recorded ${closedTrades.length} closed trades without a single loss.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Validate trade lifecycle accounting and execution resolution logic.',
    })
  }

  const breakevens = closedTrades.filter((trade) => trade.outcome === 'breakeven').length
  if (closedTrades.length >= 5 && breakevens / closedTrades.length >= 0.35) {
    healthChecks.push({
      id: 'too-many-breakevens',
      severity: 'caution',
      title: 'Too many breakevens',
      description: `${breakevens} of ${closedTrades.length} closed trades ended at breakeven.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Inspect stop-to-breakeven logic and intrabar conflict handling.',
    })
  }

  if (liveAcceptanceRate + 0.05 < baselinePositiveRate) {
    healthChecks.push({
      id: 'live-backtest-divergence',
      severity: 'critical',
      title: 'Live/backtest divergence',
      description: `Live acceptance rate is ${(liveAcceptanceRate * 100).toFixed(1)}% versus a historical frontier positive-rate baseline of ${(baselinePositiveRate * 100).toFixed(1)}%.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Compare live frontier-score distribution against the training and replay artifacts.',
    })
  }

  const collapsedSpecialists = specialists.filter((item) => item.health === 'critical').map((item) => item.key)
  if (collapsedSpecialists.length) {
    healthChecks.push({
      id: 'specialist-collapse',
      severity: 'critical',
      title: 'Specialist collapse',
      description: `${collapsedSpecialists.join(', ')} are currently degraded or disabled by live behavior.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Reduce weight or disable the affected specialist until performance recovers.',
    })
  }

  const signalShare = riskByInstrument.map((row) => row.signals)
  const totalSignals = signalShare.reduce((sum, value) => sum + value, 0)
  const maxSignalShare = totalSignals ? Math.max(...signalShare) / totalSignals : 0
  if (maxSignalShare >= 0.8 && totalSignals > 0) {
    healthChecks.push({
      id: 'exposure-concentration',
      severity: 'caution',
      title: 'Exposure concentration',
      description: `One instrument accounts for ${(maxSignalShare * 100).toFixed(0)}% of all observed live decisions.`,
      timestamp: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      action: 'Check whether cross-market diversification is actually engaging.',
    })
  }

  const overallHealth = healthChecks.some((check) => check.severity === 'critical')
    ? 'critical'
    : healthChecks.some((check) => check.severity === 'caution')
      ? 'caution'
      : 'healthy'

  const maxFreshness = Math.max(
    0,
    ...Object.values(latestMetrics.instrument_status ?? {}).map((status) =>
      toNumber(status.snapshot_latest_age_seconds, 0),
    ),
  )

  const systemMode = acceptedSignalsTotal > 0
    ? allDecisions.some((item) => item.mode === 'live')
      ? 'LIVE'
      : 'DRY RUN'
    : 'DRY RUN'

  return {
    generatedAt: new Date().toISOString(),
    session: {
      mode: systemMode,
      connectionStatus: maxFreshness > 90 ? 'disconnected' : maxFreshness > 30 ? 'degraded' : 'connected',
      brokerStatus: Object.values(latestMetrics.instrument_status ?? {}).every((status) => status.market_status === 'TRADEABLE')
        ? 'connected'
        : 'degraded',
      health: overallHealth,
      lastUpdate: latestMetrics.timestamp_utc ?? new Date().toISOString(),
      dataFreshnessSeconds: maxFreshness,
      marketSession: marketSessionForTime(latestMetrics.timestamp_utc ?? new Date().toISOString()),
      currentSessionLabel: `${String(latestMetrics.account_stage ?? 'challenge')} monitoring`,
      openPositions: toNumber(latestMetrics.open_positions_total, 0),
      activeSpecialists: new Set(latestSignals.map((item) => item.candidate?.chosen_setup).filter(Boolean)).size,
      activeSignals: latestActionableSignals.length,
      rejectedSignals: latestRejectedSignals.length,
      symbols: instruments,
      timeframes: ['1m'],
    },
    metrics: {
      totalPnl,
      dailyPnl,
      weeklyPnl,
      winRate,
      profitFactor: grossLosses > 0 ? grossWins / grossLosses : null,
      maxDrawdown: maxDrawdownPct,
      expectancy,
      trades: closedTrades.length,
      averageR,
      openRisk: latestOpenRisk,
      exposure: maxAllowedRisk > 0 ? (latestOpenRisk / maxAllowedRisk) * 100 : 0,
      slippage,
      fillQuality,
      rejectedSignals: rejectedSignalsTotal,
      activeSignals: latestActionableSignals.length,
      equityCurve,
      pnlDistribution: Object.entries(buckets).map(([bucket, value]) => ({ bucket, value })),
    },
    allocator: {
      totalCandidates: allDecisions.length,
      acceptedTrades: acceptedSignalsTotal,
      rejectedTrades: rejectedSignalsTotal,
      currentPortfolioRisk: latestOpenRisk,
      maxAllowedRisk,
      concurrentPositions: toNumber(latestMetrics.open_positions_total, 0),
      jointAllocationHealthy: !rejectionReasons.some((item) => item.reason === 'rejected_by_portfolio_correlation'),
      rejectionReasons,
      riskByInstrument,
    },
    specialists,
    healthChecks,
    trades: paperTrades,
    candlesBySymbol,
  }
}

function writeSnapshot() {
  const payload = buildDashboardSnapshot()
  fs.mkdirSync(path.dirname(outputPath), { recursive: true })
  fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2))
  console.log(`wrote ${path.relative(dashboardDir, outputPath)} at ${payload.generatedAt}`)
}

function main() {
  writeSnapshot()
  if (process.argv.includes('--watch')) {
    console.log('watching live artifacts for dashboard snapshot refresh...')
    let previous = ''
    setInterval(() => {
      const current = JSON.stringify([
        fs.existsSync(path.join(repoRoot, 'artifacts', 'live_capital', 'server_metrics.jsonl'))
          ? fs.statSync(path.join(repoRoot, 'artifacts', 'live_capital', 'server_metrics.jsonl')).mtimeMs
          : 0,
        fs.existsSync(path.join(repoRoot, 'artifacts', 'live_capital', '_paper_state.json'))
          ? fs.statSync(path.join(repoRoot, 'artifacts', 'live_capital', '_paper_state.json')).mtimeMs
          : 0,
        ...instruments.flatMap((instrument) => [
          fs.existsSync(path.join(repoRoot, 'artifacts', 'live_capital', instrument.toLowerCase(), 'live_decisions.jsonl'))
            ? fs.statSync(path.join(repoRoot, 'artifacts', 'live_capital', instrument.toLowerCase(), 'live_decisions.jsonl')).mtimeMs
            : 0,
          fs.existsSync(path.join(repoRoot, 'artifacts', 'live_snapshots', `${instrument.toLowerCase()}_live_snapshot.csv.gz`))
            ? fs.statSync(path.join(repoRoot, 'artifacts', 'live_snapshots', `${instrument.toLowerCase()}_live_snapshot.csv.gz`)).mtimeMs
            : 0,
        ]),
      ])
      if (current !== previous) {
        previous = current
        writeSnapshot()
      }
    }, 5000)
  }
}

main()
