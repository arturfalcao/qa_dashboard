'use client'

import * as React from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XIcon } from 'lucide-react'
import { Fragment } from 'react'
import { Button } from './button'
import { cn } from '@/lib/utils'

export interface ModalProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  description?: React.ReactNode
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
  showCloseButton?: boolean
  initialFocus?: React.MutableRefObject<HTMLElement | null>
}

const sizeClasses: Record<NonNullable<ModalProps['size']>, string> = {
  sm: 'max-w-md',
  md: 'max-w-2xl',
  lg: 'max-w-4xl',
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  size = 'md',
  showCloseButton = true,
  initialFocus,
}: ModalProps) {
  return (
    <Transition show={open} as={Fragment} appear>
      <Dialog as="div" className="relative z-50" onClose={onClose} initialFocus={initialFocus}>
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

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center px-4 py-8">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="translate-y-2 opacity-0"
              enterTo="translate-y-0 opacity-100"
              leave="ease-in duration-150"
              leaveFrom="translate-y-0 opacity-100"
              leaveTo="translate-y-2 opacity-0"
            >
              <Dialog.Panel className={cn('w-full rounded-2xl bg-white shadow-lg dark:bg-neutral-900', sizeClasses[size])}>
                <div className="flex items-start justify-between gap-4 border-b border-neutral-200 px-6 py-4 dark:border-neutral-800">
                  <div>
                    {title && (
                      <Dialog.Title className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
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
                      aria-label="Close dialog"
                    >
                      <XIcon className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                <div className="px-6 py-6">{children}</div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

export interface ModalFooterProps {
  children: React.ReactNode
  align?: 'start' | 'center' | 'end' | 'between'
}

export function ModalFooter({ children, align = 'end' }: ModalFooterProps) {
  const alignment = {
    start: 'justify-start',
    center: 'justify-center',
    end: 'justify-end',
    between: 'justify-between',
  }[align]

  return (
    <div className={cn('flex items-center gap-3 border-t border-neutral-200 px-6 py-4 dark:border-neutral-800', alignment)}>
      {children}
    </div>
  )
}
