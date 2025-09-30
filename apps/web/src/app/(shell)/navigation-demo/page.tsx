'use client'

import {
  ActivityIcon,
  PackageIcon,
  BarChart3Icon,
  ArrowRightIcon,
} from 'lucide-react'
import { AppShell } from '@/components/navigation/app-shell'
import { SidebarItem } from '@/components/ui/sidebar'

const demoNavigation: SidebarItem[] = [
  { label: 'Live Feed', href: '/navigation-demo/feed', icon: ActivityIcon },
  { label: 'Lots', href: '/navigation-demo/lots', icon: PackageIcon },
  { label: 'Analytics', href: '/navigation-demo/analytics', icon: BarChart3Icon },
]

export default function NavigationDemoPage() {
  return (
    <AppShell
      navigation={demoNavigation}
      tenantLabel="Demo Workspace"
      breadcrumbTrail={[
        { label: 'Navigation demo', href: '/navigation-demo' },
      ]}
    >
      <div className="space-y-6 rounded-2xl border border-dashed border-neutral-200 bg-white p-10 text-neutral-700 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">Navigation shell demo</h1>
        <p>
          This route lives under <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600">src/app/(shell)/navigation-demo</code>. It uses
          <code className="ml-1 rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600">&lt;AppShell /&gt;</code> to compose a responsive sidebar, breadcrumb-aware topbar, command palette, and keyboard navigation helpers.
        </p>
        <ul className="space-y-2 text-sm">
          <li className="flex items-center gap-2">
            <ArrowRightIcon className="h-4 w-4 text-primary-500" />
            Resize to mobile to see the sheet-based navigation.
          </li>
          <li className="flex items-center gap-2">
            <ArrowRightIcon className="h-4 w-4 text-primary-500" />
            Press <kbd className="rounded border border-neutral-300 bg-neutral-100 px-1 text-xs">⌘</kbd>
            <span> + </span>
            <kbd className="rounded border border-neutral-300 bg-neutral-100 px-1 text-xs">K</kbd> to open the command palette.
          </li>
        </ul>
      </div>
    </AppShell>
  )
}
