/* eslint-disable react-refresh/only-export-components */
import type { ComponentProps, ReactNode } from 'react'

import * as TooltipPrimitive from '@radix-ui/react-tooltip'

import { cn } from '@/lib/utils'

export function TooltipProvider({ children }: { children: ReactNode }) {
  return <TooltipPrimitive.Provider delayDuration={150}>{children}</TooltipPrimitive.Provider>
}

export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  className,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        className={cn('z-50 rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-slate-200 shadow-lg', className)}
        sideOffset={8}
        {...props}
      />
    </TooltipPrimitive.Portal>
  )
}
