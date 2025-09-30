'use client'

import * as React from 'react'
import { CalendarIcon } from 'lucide-react'
import { Input, InputProps } from './input'

export interface DateInputProps extends Omit<InputProps, 'type' | 'value' | 'onChange'> {
  value?: string
  onChange?: (value: string) => void
  min?: string
  max?: string
}

export function DateInput({ value, onChange, min, max, ...props }: DateInputProps) {
  return (
    <Input
      {...props}
      type="date"
      value={value}
      onChange={(event) => onChange?.(event.target.value)}
      startIcon={props.startIcon ?? <CalendarIcon className="h-4 w-4" />}
      min={min}
      max={max}
    />
  )
}

export interface DateRangeValue {
  start?: string
  end?: string
}

export interface DateRangeInputProps {
  startId: string
  endId: string
  value: DateRangeValue
  onChange: (value: DateRangeValue) => void
  min?: string
  max?: string
  className?: string
}

export function DateRangeInput({
  startId,
  endId,
  value,
  onChange,
  min,
  max,
  className,
}: DateRangeInputProps) {
  return (
    <div className={className}>
      <div className="grid gap-3 sm:grid-cols-2">
        <DateInput
          id={startId}
          value={value.start}
          min={min}
          max={value.end ?? max}
          onChange={(start) => onChange({ ...value, start })}
          helperText="Start date"
        />
        <DateInput
          id={endId}
          value={value.end}
          min={value.start ?? min}
          max={max}
          onChange={(end) => onChange({ ...value, end })}
          helperText="End date"
        />
      </div>
    </div>
  )
}
