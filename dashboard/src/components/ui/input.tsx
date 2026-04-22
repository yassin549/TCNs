import type { InputHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-11 w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-sky-400/45 focus:ring-2 focus:ring-sky-400/15',
        className,
      )}
      {...props}
    />
  )
}
