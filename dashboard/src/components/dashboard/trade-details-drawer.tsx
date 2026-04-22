import { ArrowRightLeft, CircleAlert, Gauge } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatCurrency, formatDateTime, formatSigned } from '@/lib/format'
import type { Trade } from '@/types/trading'

export function TradeDetailsDrawer({
  trade,
  open,
  onOpenChange,
}: {
  trade: Trade | null
  open: boolean
  onOpenChange: (value: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {trade ? (
          <ScrollArea className="min-h-0 flex-1 pr-2">
            <div className="space-y-5">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
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
                  <Badge variant="outline">{trade.status}</Badge>
                  <Badge variant="outline">{trade.direction}</Badge>
                  <Badge variant="outline">{trade.specialist}</Badge>
                </div>
                <div>
                  <DialogTitle className="text-2xl font-semibold text-white">{trade.symbol}</DialogTitle>
                  <DialogDescription className="mt-2 text-sm leading-6 text-slate-400">
                    {trade.context} / {trade.regime}
                  </DialogDescription>
                </div>
              </div>

              <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                  <Gauge className="size-3.5" />
                  Trade summary
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <Detail label="Entry" value={`${trade.entryPrice.toFixed(1)} / ${formatDateTime(trade.entryTime)}`} />
                  <Detail
                    label="Exit"
                    value={
                      trade.exitPrice
                        ? `${trade.exitPrice.toFixed(1)} / ${formatDateTime(trade.exitTime ?? trade.entryTime)}`
                        : 'Position open'
                    }
                  />
                  <Detail label="Stop / target" value={`${trade.stopPrice.toFixed(1)} / ${trade.targetPrice.toFixed(1)}`} />
                  <Detail label="Size" value={`${trade.size}`} />
                  <Detail label="PnL" value={`${formatCurrency(trade.pnl)} / ${formatSigned(trade.pnlR)}R`} />
                  <Detail
                    label="Slippage / fill"
                    value={`${trade.slippageBps === null ? 'n/a' : `${trade.slippageBps.toFixed(1)} bps`} / ${
                      trade.fillQuality === null ? 'n/a' : `${trade.fillQuality.toFixed(0)}%`
                    }`}
                  />
                </div>
              </div>

              <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                  <ArrowRightLeft className="size-3.5" />
                  Decision trail
                </div>
                <div className="mt-4 space-y-3">
                  <ReasonBlock label="Entry reason" value={trade.entryReason} />
                  <ReasonBlock label="Exit reason" value={trade.exitReason} />
                </div>
              </div>

              {trade.warnings?.length ? (
                <div className="rounded-[20px] border border-amber-500/20 bg-amber-500/10 p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-amber-200">
                    <CircleAlert className="size-3.5" />
                    Warnings
                  </div>
                  <div className="mt-3 space-y-2">
                    {trade.warnings.map((warning) => (
                      <div key={warning} className="rounded-[16px] border border-amber-400/10 bg-black/10 p-3 text-sm text-amber-100">
                        {warning}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </ScrollArea>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-white/10 bg-slate-950/35 p-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-sm leading-6 text-white">{value}</div>
    </div>
  )
}

function ReasonBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-white/8 bg-slate-950/35 p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <p className="mt-2 text-sm leading-6 text-slate-300">{value}</p>
    </div>
  )
}
