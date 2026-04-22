/* eslint-disable react-refresh/only-export-components */
import type { ComponentProps, ReactNode } from 'react'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'

import { cn } from '@/lib/utils'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

export function DialogContent({
  className,
  children,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content> & { children?: ReactNode }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-950/45 backdrop-blur-[2px] data-[state=closed]:animate-[overlay-out_160ms_ease-in_forwards] data-[state=open]:animate-[overlay-in_180ms_ease-out]" />
      <DialogPrimitive.Content
        className={cn(
          'fixed inset-y-4 right-4 z-50 flex w-[min(520px,calc(100vw-2rem))] max-w-full flex-col overflow-hidden rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(12,16,23,0.98),rgba(8,11,17,0.96))] p-6 shadow-[0_32px_100px_rgba(0,0,0,0.45)] data-[state=closed]:animate-[drawer-out_160ms_ease-in_forwards] data-[state=open]:animate-[drawer-in_220ms_ease-out]',
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-2xl border border-white/10 bg-white/[0.03] p-2 text-slate-300 transition hover:bg-white/[0.08]">
          <X className="size-4" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

export const DialogTitle = DialogPrimitive.Title
export const DialogDescription = DialogPrimitive.Description
