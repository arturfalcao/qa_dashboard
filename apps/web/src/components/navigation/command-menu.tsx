'use client'

import * as React from 'react'
import { Fragment, useMemo } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { SearchIcon, ArrowUpRightIcon } from 'lucide-react'
import { useRouter } from 'next/navigation'

export interface CommandItem {
  label: string
  href: string
  description?: string
}

export interface CommandMenuProps {
  items: CommandItem[]
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandMenu({ items, open, onOpenChange }: CommandMenuProps) {
  const router = useRouter()
  const [query, setQuery] = React.useState('')
  const inputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 40)
    } else {
      setQuery('')
    }
  }, [open])

  const filteredItems = useMemo(() => {
    if (!query.trim()) return items
    const lower = query.toLowerCase()
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(lower) ||
        item.description?.toLowerCase().includes(lower),
    )
  }, [items, query])

  const handleSelect = (item: CommandItem) => {
    onOpenChange(false)
    router.push(item.href)
  }

  return (
    <Transition appear show={open} as={Fragment}>
      <Dialog as="div" className="relative z-[60]" onClose={onOpenChange}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-sm" aria-hidden />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-start justify-center px-4 py-16">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="scale-95 opacity-0"
              enterTo="scale-100 opacity-100"
              leave="ease-in duration-150"
              leaveFrom="scale-100 opacity-100"
              leaveTo="scale-95 opacity-0"
            >
              <Dialog.Panel className="w-full max-w-xl overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl focus:outline-none dark:border-neutral-800 dark:bg-neutral-900">
                <div className="flex items-center gap-3 border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
                  <SearchIcon className="h-4 w-4 text-neutral-400" aria-hidden />
                  <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    className="w-full bg-transparent text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none dark:text-neutral-100"
                    placeholder="Search destinations, analytics, lots…"
                  />
                  <kbd className="hidden rounded-md border border-neutral-200 bg-neutral-100 px-1.5 text-xs font-medium text-neutral-500 sm:block">
                    Esc
                  </kbd>
                </div>

                <div className="max-h-80 overflow-y-auto py-2">
                  {filteredItems.length === 0 ? (
                    <p className="px-4 py-6 text-sm text-neutral-500 dark:text-neutral-400">
                      No matches for “{query}”.
                    </p>
                  ) : (
                    <ul className="space-y-1 px-2">
                      {filteredItems.map((item) => (
                        <li key={item.href}>
                          <button
                            type="button"
                            onClick={() => handleSelect(item)}
                            className="flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left text-sm text-neutral-700 transition hover:bg-primary-50 hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:text-neutral-200 dark:hover:bg-primary-500/10"
                          >
                            <span>
                              <span className="font-medium">{item.label}</span>
                              {item.description && (
                                <span className="block text-xs text-neutral-500 dark:text-neutral-400">
                                  {item.description}
                                </span>
                              )}
                            </span>
                            <ArrowUpRightIcon className="h-4 w-4 shrink-0 text-neutral-300" aria-hidden />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
