import type { Metadata } from 'next'
import './globals.css'
import { QueryProvider } from '@/components/providers/query-provider'
import { AuthProvider } from '@/components/providers/auth-provider'
import { ToastProvider } from '@/components/ui/toast'

export const metadata: Metadata = {
  title: 'QA Dashboard',
  description: 'Quality assurance operations platform for textile manufacturing',
  keywords: ['quality assurance', 'QA dashboard', 'textile manufacturing', 'defect tracking', 'supply chain'],
  creator: 'Pack & Polish',
  publisher: 'Pack & Polish',
  icons: {
    icon: [
      { url: '/logo/PackPolish_icon_128.png', sizes: '128x128', type: 'image/png' },
      { url: '/logo/PackPolish_icon_256.png', sizes: '256x256', type: 'image/png' },
      { url: '/logo/PackPolish_icon_512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/logo/PackPolish_icon_256.png', sizes: '256x256', type: 'image/png' },
    ],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="font-sans">
        <QueryProvider>
          <AuthProvider>
            <ToastProvider>{children}</ToastProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
