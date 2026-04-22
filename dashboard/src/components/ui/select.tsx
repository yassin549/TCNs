/* eslint-disable react-refresh/only-export-components */
import type { ComponentProps, ReactNode } from 'react'

import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'

import { cn } from '@/lib/utils'

export const Select = SelectPrimitive.Root
export const SelectValue = SelectPrimitive.Value

export function SelectTrigger({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Trigger> & { children?: ReactNode }) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        'inline-flex h-11 items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 text-sm text-slate-100 outline-none transition hover:bg-white/[0.07] focus-visible:border-sky-400/45 focus-visible:ring-2 focus-visible:ring-sky-400/15 data-[placeholder]:text-slate-500',
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon>
        <ChevronDown className="size-4 text-slate-400" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

export function SelectContent({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Content> & { children?: ReactNode }) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        className={cn(
          'z-50 overflow-hidden rounded-[20px] border border-white/10 bg-slate-950/96 p-1.5 shadow-[0_24px_60px_rgba(0,0,0,0.45)]',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

export function SelectItem({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Item> & { children?: ReactNode }) {
  return (
    <SelectPrimitive.Item
      className={cn(
        'relative flex cursor-default items-center rounded-2xl py-2.5 pl-9 pr-3 text-sm text-slate-200 outline-none data-[highlighted]:bg-white/[0.09] data-[state=checked]:bg-sky-400/10 data-[state=checked]:text-sky-100',
        className,
      )}
      {...props}
    >
      <span className="absolute left-2.5 flex size-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="size-4" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
}
