'use client'

import * as React from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { XIcon } from 'lucide-react'
import { Button } from './button'
import { cn } from '@/lib/utils'

export type SheetSide = 'left' | 'right' | 'top' | 'bottom'

export interface SheetProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  description?: React.ReactNode
  children: React.ReactNode
  side?: SheetSide
  size?: 'sm' | 'md' | 'lg'
  showCloseButton?: boolean
}

const sideClasses: Record<SheetSide, string> = {
  left: 'inset-y-0 left-0 w-full max-w-md',
  right: 'inset-y-0 right-0 w-full max-w-md',
  top: 'inset-x-0 top-0 h-auto max-h-[90vh]',
  bottom: 'inset-x-0 bottom-0 h-auto max-h-[90vh]',
}

const sizeModifiers: Record<SheetProps['size'], string> = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-xl',
}

export function Sheet({
  open,
  onClose,
  title,
  description,
  children,
  side = 'right',
  size = 'md',
  showCloseButton = true,
}: SheetProps) {
  return (
    <Transition show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-neutral-900/30 backdrop-blur-sm" aria-hidden />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 flex">
            <Transition.Child
              as={Fragment}
              enter="transform transition ease-out duration-300"
              enterFrom={cn(
                side === 'left' && '-translate-x-full',
                side === 'right' && 'translate-x-full',
                side === 'top' && '-translate-y-full',
                side === 'bottom' && 'translate-y-full',
              )}
              enterTo="translate-x-0 translate-y-0"
              leave="transform transition ease-in duration-200"
              leaveFrom="translate-x-0 translate-y-0"
              leaveTo={cn(
                side === 'left' && '-translate-x-full',
                side === 'right' && 'translate-x-full',
                side === 'top' && '-translate-y-full',
                side === 'bottom' && 'translate-y-full',
              )}
            >
              <Dialog.Panel
                className={cn(
                  'flex h-full w-full flex-col border border-neutral-200 bg-white shadow-xl dark:border-neutral-800 dark:bg-neutral-900',
                  sideClasses[side],
                  side !== 'top' && side !== 'bottom' && sizeModifiers[size],
                )}
              >
                <div className="flex items-start justify-between gap-4 border-b border-neutral-200 px-6 py-4 dark:border-neutral-800">
                  <div>
                    {title && (
                      <Dialog.Title className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                        {title}
                      </Dialog.Title>
                    )}
                    {description && (
                      <Dialog.Description className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                        {description}
                      </Dialog.Description>
                    )}
                  </div>

                  {showCloseButton && (
                    <Button
                      variant="subtle"
                      size="sm"
                      className="text-neutral-500 hover:text-neutral-700"
                      onClick={onClose}
                      aria-label="Close panel"
                    >
                      <XIcon className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto px-6 py-6">{children}</div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
