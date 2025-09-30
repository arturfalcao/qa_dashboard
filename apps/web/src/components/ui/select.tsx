'use client'

import * as React from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { CheckIcon, ChevronDownIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SelectOption<TValue = string> {
  label: string
  value: TValue
  description?: string
  disabled?: boolean
}

export interface SelectProps<TValue> {
  id?: string
  value: TValue
  onChange: (value: TValue) => void
  options: SelectOption<TValue>[]
  placeholder?: string
  disabled?: boolean
  className?: string
}

export function Select<TValue>({
  id,
  value,
  onChange,
  options,
  placeholder = 'Select…',
  disabled,
  className,
}: SelectProps<TValue>) {
  const selectedOption = options.find((option) => option.value === value)

  return (
    <Listbox value={value} onChange={onChange} disabled={disabled}>
      {({ open }) => (
        <div className={cn('relative', className)}>
          <Listbox.Button
            id={id}
            className={cn(
              'flex w-full items-center justify-between rounded-md border border-neutral-200 bg-white px-3 py-2 text-left text-sm text-neutral-900 shadow-sm transition focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-transparent dark:text-neutral-100',
            )}
          >
            <span className="flex-1 truncate">
              {selectedOption ? selectedOption.label : <span className="text-neutral-400">{placeholder}</span>}
            </span>
            <ChevronDownIcon
              className={cn('h-4 w-4 text-neutral-400 transition-transform', open && 'rotate-180')}
              aria-hidden
            />
          </Listbox.Button>

          <Transition
            show={open}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options
              className="absolute z-20 mt-2 max-h-60 w-full overflow-auto rounded-lg border border-neutral-200 bg-white py-1 text-sm shadow-lg focus:outline-none dark:bg-neutral-900"
            >
              {options.map((option) => (
                <Listbox.Option
                  key={String(option.value)}
                  value={option.value}
                  disabled={option.disabled}
                  className={({ active, disabled: isDisabled }) =>
                    cn(
                      'flex cursor-pointer select-none items-start gap-2 px-3 py-2 text-neutral-700 dark:text-neutral-200',
                      active && 'bg-primary-50 text-primary-700 dark:bg-primary-600/20 dark:text-primary-200',
                      isDisabled && 'cursor-not-allowed opacity-50',
                    )
                  }
                >
                  {({ selected }) => (
                    <>
                      <span className={cn('mt-0.5 h-4 w-4 text-primary-600', !selected && 'opacity-0')} aria-hidden>
                        <CheckIcon className="h-4 w-4" />
                      </span>
                      <span className="flex flex-col">
                        <span className={cn('font-medium', selected && 'text-primary-700 dark:text-primary-200')}>
                          {option.label}
                        </span>
                        {option.description && (
                          <span className="text-xs text-neutral-500 dark:text-neutral-400">{option.description}</span>
                        )}
                      </span>
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      )}
    </Listbox>
  )
}
