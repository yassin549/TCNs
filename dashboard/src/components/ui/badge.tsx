import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em]',
  {
    variants: {
      variant: {
        neutral: 'border-white/10 bg-white/5 text-slate-200',
        healthy: 'border-emerald-500/30 bg-emerald-500/12 text-emerald-300',
        caution: 'border-amber-500/30 bg-amber-500/12 text-amber-300',
        critical: 'border-rose-500/30 bg-rose-500/12 text-rose-300',
        outline: 'border-white/15 bg-transparent text-slate-300',
      },
    },
    defaultVariants: {
      variant: 'neutral',
    },
  },
)

export function Badge({
  className,
  variant,
  ...props
}: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

