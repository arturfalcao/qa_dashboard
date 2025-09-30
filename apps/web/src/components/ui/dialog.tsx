'use client'

import * as React from 'react'
import { Dialog as HeadlessDialog, Transition } from '@headlessui/react'
import { XIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  return (
    <Transition show={open} as={React.Fragment}>
      <HeadlessDialog onClose={() => onOpenChange(false)} className="relative z-50">
        <Transition.Child
          as={React.Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            as={React.Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            {children}
          </Transition.Child>
        </div>
      </HeadlessDialog>
    </Transition>
  )
}

interface DialogContentProps {
  children: React.ReactNode
  className?: string
}

export function DialogContent({ children, className }: DialogContentProps) {
  return (
    <HeadlessDialog.Panel
      className={cn(
        'w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all',
        className
      )}
    >
      {children}
    </HeadlessDialog.Panel>
  )
}

export function DialogHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('mb-4', className)}>{children}</div>
}

export function DialogTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <HeadlessDialog.Title as="h3" className={cn('text-lg font-semibold leading-6 text-slate-900', className)}>
      {children}
    </HeadlessDialog.Title>
  )
}

export function DialogDescription({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <HeadlessDialog.Description as="p" className={cn('mt-2 text-sm text-slate-500', className)}>
      {children}
    </HeadlessDialog.Description>
  )
}

export function DialogFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('mt-6 flex justify-end gap-3', className)}>{children}</div>
}
