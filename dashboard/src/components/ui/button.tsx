import type { ButtonHTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-2xl px-4 py-2.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/20',
  {
    variants: {
      variant: {
        primary: 'bg-sky-400 text-slate-950 hover:bg-sky-300',
        ghost: 'border border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/[0.08]',
        neutral: 'border border-white/8 bg-slate-900/80 text-slate-300 hover:bg-slate-800/90',
      },
    },
    defaultVariants: {
      variant: 'ghost',
    },
  },
)

export function Button({
  className,
  variant,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant }), className)} {...props} />
}
