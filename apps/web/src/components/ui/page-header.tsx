import { cn } from '@/lib/utils'

interface PageHeaderProps {
  title: string
  description?: string
  meta?: React.ReactNode
  actions?: React.ReactNode
  align?: 'start' | 'center' | 'end'
  className?: string
}

export function PageHeader({
  title,
  description,
  meta,
  actions,
  align = 'start',
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between',
        align === 'center' && 'sm:items-center',
        align === 'end' && 'sm:items-end',
        className,
      )}
    >
      <div className="space-y-2">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">{title}</h1>
          {description && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">{description}</p>
          )}
        </div>
        {meta && <div className="text-xs text-neutral-500 dark:text-neutral-400">{meta}</div>}
      </div>
      {actions && <div className="flex items-center gap-2 sm:justify-end">{actions}</div>}
    </div>
  )
}
