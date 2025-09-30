'use client'

import { ChevronLeftIcon, ChevronRightIcon, MoreHorizontalIcon } from 'lucide-react'
import { Button } from './button'
import { cn } from '@/lib/utils'

export interface PaginationProps {
  page: number
  pageCount: number
  onPageChange: (page: number) => void
  className?: string
  siblingCount?: number
  hideIfSinglePage?: boolean
}

export function Pagination({
  page,
  pageCount,
  onPageChange,
  className,
  siblingCount = 1,
  hideIfSinglePage = true,
}: PaginationProps) {
  if (pageCount <= 1 && hideIfSinglePage) return null

  const clampedPage = Math.max(1, Math.min(page, pageCount))
  const pages = buildPages(clampedPage, pageCount, siblingCount)

  return (
    <nav className={cn('flex items-center justify-between gap-4 text-sm text-neutral-600', className)} aria-label="Pagination">
      <Button
        variant="subtle"
        size="sm"
        icon={<ChevronLeftIcon className="h-4 w-4" />}
        iconPosition="start"
        onClick={() => onPageChange(clampedPage - 1)}
        disabled={clampedPage === 1}
      >
        Previous
      </Button>

      <ol className="flex items-center gap-1">
        {pages.map((item, index) => {
          if (item === 'ellipsis') {
            return (
              <li key={`ellipsis-${index}`} aria-hidden>
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-md text-neutral-400">
                  <MoreHorizontalIcon className="h-4 w-4" />
                </span>
              </li>
            )
          }

          const isActive = item === clampedPage
          return (
            <li key={item}>
              <button
                type="button"
                onClick={() => onPageChange(item)}
                className={cn(
                  'flex h-9 w-9 items-center justify-center rounded-md border border-transparent text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-400',
                  isActive
                    ? 'border-primary-200 bg-primary-50 text-primary-700 shadow-sm'
                    : 'text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-800',
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                {item}
              </button>
            </li>
          )
        })}
      </ol>

      <Button
        variant="subtle"
        size="sm"
        icon={<ChevronRightIcon className="h-4 w-4" />}
        iconPosition="end"
        onClick={() => onPageChange(clampedPage + 1)}
        disabled={clampedPage === pageCount}
      >
        Next
      </Button>
    </nav>
  )
}

type PageItem = number | 'ellipsis'

function buildPages(current: number, total: number, siblingCount: number): PageItem[] {
  const pages: PageItem[] = []
  const totalDisplayed = siblingCount * 2 + 3 // current + siblings + first and last
  const showLeftEllipsis = current - siblingCount > 2
  const showRightEllipsis = current + siblingCount < total - 1

  const startPage = showLeftEllipsis ? current - siblingCount : 1
  const endPage = showRightEllipsis ? current + siblingCount : total

  pages.push(1)
  for (let page = Math.max(startPage, 2); page <= Math.min(endPage, total - 1); page++) {
    pages.push(page)
  }
  if (total > 1) {
    pages.push(total)
  }

  if (showLeftEllipsis) {
    pages.splice(1, 0, 'ellipsis')
  }
  if (showRightEllipsis) {
    pages.splice(pages.length - 1, 0, 'ellipsis')
  }

  return Array.from(new Set(pages)).filter((value, index, array) => !(value === 'ellipsis' && array[index - 1] === 'ellipsis'))
}
