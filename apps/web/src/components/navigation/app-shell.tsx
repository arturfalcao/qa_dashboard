'use client'

import * as React from 'react'
import { Sidebar, SidebarItem } from '@/components/ui/sidebar'
import { Navbar, BreadcrumbItem } from '@/components/ui/navbar'
import { Sheet } from '@/components/ui/sheet'
import { CommandMenu, CommandItem } from './command-menu'
import { cn } from '@/lib/utils'

export interface AppShellProps {
  navigation: SidebarItem[]
  children: React.ReactNode
  breadcrumbTrail?: BreadcrumbItem[]
  tenantLabel?: string
  actions?: React.ReactNode
  sidebarFooter?: React.ReactNode
  contentClassName?: string
}

export function AppShell({
  navigation,
  children,
  breadcrumbTrail,
  tenantLabel,
  actions,
  sidebarFooter,
  contentClassName,
}: AppShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false)
  const [commandOpen, setCommandOpen] = React.useState(false)

  React.useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().includes('MAC')
      const modifierPressed = isMac ? event.metaKey : event.ctrlKey
      if (modifierPressed && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen((prev) => !prev)
      }
    }

    window.addEventListener('keydown', handleKeydown)
    return () => window.removeEventListener('keydown', handleKeydown)
  }, [])

  const commandItems: CommandItem[] = React.useMemo(
    () =>
      navigation.map((item) => ({
        label: item.label,
        href: item.href,
        description: item.description,
      })),
    [navigation],
  )

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-50">
      <a
        href="#app-shell-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[80] focus:rounded-md focus:bg-primary-600 focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to main content
      </a>

      <CommandMenu items={commandItems} open={commandOpen} onOpenChange={setCommandOpen} />

      <Navbar
        tenantLabel={tenantLabel}
        breadcrumbs={breadcrumbTrail}
        actions={actions}
        onToggleNavigation={() => setMobileNavOpen((prev) => !prev)}
        onOpenCommandMenu={() => setCommandOpen(true)}
        isMobileNavOpen={mobileNavOpen}
      />

      <div className="flex w-full pt-16">
        <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] w-72 shrink-0 lg:block">
          <Sidebar items={navigation} footer={sidebarFooter} className="h-full overflow-y-auto" />
        </aside>

        <main
          id="app-shell-main"
          className={cn(
            'flex-1 bg-neutral-50 px-4 pb-8 pt-0 sm:px-6 lg:px-10',
            'max-w-full lg:max-w-[calc(100%-18rem)]',
            contentClassName,
          )}
        >
          <div className="mx-auto w-full max-w-6xl space-y-8">
            {children}
          </div>
        </main>
      </div>

      <Sheet open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} title="Navigation" description={tenantLabel} side="left">
        <Sidebar
          items={navigation}
          onNavigate={() => setMobileNavOpen(false)}
          footer={sidebarFooter}
          className="h-full overflow-y-auto"
        />
      </Sheet>
    </div>
  )
}
