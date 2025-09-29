'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/providers/auth-provider'
import { apiClient } from '@/lib/api'
import { storeUser } from '@/lib/auth'
import { UserRole } from '@qa-dashboard/shared'

const featureHighlights = [
  {
    title: 'Insights in seconds',
    description:
      'Monitor production quality trends across every factory with interactive dashboards and live alerts.',
  },
  {
    title: 'Collaborative reviews',
    description:
      'Bring operators and supervisors together with shared workspaces tailored to their responsibilities.',
  },
  {
    title: 'Scalable governance',
    description:
      'Standardise audits, streamline approvals, and build trust with a single source of truth for QA data.',
  },
]

const demoAccounts = [
  {
    name: 'Carlos Martins',
    email: 'carlos.martins@paco.example',
    focus: 'Production Quality Lead',
  },
  {
    name: 'Inês Azevedo',
    email: 'ines.azevedo@paco.example',
    focus: 'Supplier Performance',
  },
  {
    name: 'Joana Costa',
    email: 'joana.costa@paco.example',
    focus: 'Customer Care Feedback',
  },
  {
    name: 'Miguel Lopes',
    email: 'miguel.lopes@paco.example',
    focus: 'Factory Operations',
  },
]

const sharedPassword = 'demo1234'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [copiedUser, setCopiedUser] = useState<string | null>(null)
  const { setUser } = useAuth()
  const router = useRouter()
  const copyTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current)
      }
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const response = await apiClient.login({ email, password })

      let tenantSlug: string | null = null
      let tenantName: string | null = null

      if (response.user.tenantId) {
        try {
          const tenant = await apiClient.getTenantById(response.user.tenantId)
          tenantSlug = tenant.slug
          tenantName = tenant.name
        } catch (tenantError) {
          console.error('Failed to load tenant information', tenantError)
        }
      }

      const userWithTenant = {
        ...response.user,
        tenantSlug,
        tenantName,
      }

      storeUser(userWithTenant)
      setUser(userWithTenant)

      // Check for super admin
      const isSuperAdmin = email === 'celso.silva@packpolish.com'
      if (isSuperAdmin) {
        router.push('/admin')
        return
      }

      const isOperator = response.user.roles.some((role) =>
        [UserRole.OPERATOR, UserRole.SUPERVISOR].includes(role),
      )

      if (isOperator) {
        router.push('/operator')
      } else {
        if (tenantSlug) {
          router.push(`/c/${tenantSlug}/feed`)
        } else {
          router.push('/')
        }
      }
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopyCredential = async (accountEmail: string) => {
    if (copyTimeoutRef.current) {
      clearTimeout(copyTimeoutRef.current)
    }

    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(`${accountEmail}\t${sharedPassword}`)
      }
      setCopiedUser(accountEmail)
    } catch (copyError) {
      console.error('Failed to copy demo credentials', copyError)
      setCopiedUser(accountEmail)
    } finally {
      copyTimeoutRef.current = setTimeout(() => {
        setCopiedUser(null)
      }, 2000)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950">
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-y-0 right-[-20%] h-[140%] w-[70%] rounded-full bg-gradient-to-br from-primary-500/40 via-primary-700/20 to-slate-900 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-6 py-12 sm:px-8 lg:grid lg:grid-cols-12 lg:gap-12 lg:px-12">
        <section className="relative hidden overflow-hidden rounded-3xl bg-gradient-to-br from-primary-700 via-slate-900 to-slate-950 p-12 text-white shadow-2xl lg:col-span-6 xl:col-span-7 lg:flex lg:flex-col">
          <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.3em] text-primary-100">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-lg font-bold">
              QA
            </span>
            <span>Quality Assurance Platform</span>
          </div>

          <div className="mt-12 max-w-xl">
            <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
              Transform QA operations into a connected, data-driven experience.
            </h1>
            <p className="mt-6 text-base text-primary-100/90">
              Empower teams to spot anomalies faster, reduce waste, and deliver exceptional products with confidence.
            </p>
          </div>

          <ul className="mt-12 space-y-8">
            {featureHighlights.map((feature) => (
              <li key={feature.title} className="flex gap-4">
                <span className="mt-1 flex h-10 w-10 flex-none items-center justify-center rounded-full bg-white/10">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    className="h-6 w-6"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </span>
                <div>
                  <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                  <p className="mt-2 text-sm text-primary-100/80">{feature.description}</p>
                </div>
              </li>
            ))}
          </ul>

          <div className="mt-auto pt-12">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-6 backdrop-blur">
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-primary-100/70">Case study</p>
              <p className="mt-3 text-base font-semibold text-white">
                “After centralising quality data with QA Dashboard we reduced incident response time by 36% and gave every plant
                access to the same insights.”
              </p>
              <p className="mt-4 text-sm text-primary-100/70">Ana Ribeiro — Director of Quality, PA&amp;CO</p>
            </div>
          </div>
        </section>

        <section className="relative z-10 col-span-12 mx-auto w-full max-w-xl lg:col-span-6 xl:col-span-5 lg:ml-auto">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-primary-600/10 text-lg font-bold text-primary-600">
              QA
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-primary-600">QA Dashboard</p>
              <p className="text-base font-semibold text-white">Sign in to orchestrate your quality strategy</p>
            </div>
          </div>

          <div className="rounded-3xl bg-white/90 p-8 shadow-2xl backdrop-blur-sm sm:p-10">
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-slate-900">Welcome back</h2>
              <p className="mt-2 text-sm text-slate-500">
                Access personalised dashboards, review audits, and coordinate with your team.
              </p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit} noValidate>
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-2xl border border-danger-100 bg-danger-50/80 px-4 py-3 text-sm text-danger-700"
                >
                  <span className="mt-0.5 inline-flex h-6 w-6 flex-none items-center justify-center rounded-full bg-danger-100 text-danger-600">
                    !
                  </span>
                  <span className="leading-relaxed">{error}</span>
                </div>
              )}

              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-semibold text-slate-700">
                  Email address
                </label>
                <div className="relative">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    aria-invalid={Boolean(error)}
                    className="peer block w-full rounded-2xl border border-slate-200 bg-slate-50/60 px-4 py-3 text-base font-medium text-slate-900 shadow-sm transition focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200 focus:ring-offset-2 focus:ring-offset-white"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <div className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-slate-400">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      className="h-5 w-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M2.25 6.75l8.954 5.257a1.5 1.5 0 001.492 0L21.75 6.75m-19.5 0a1.5 1.5 0 011.5-1.5h15a1.5 1.5 0 011.5 1.5v10.5a1.5 1.5 0 01-1.5 1.5h-15a1.5 1.5 0 01-1.5-1.5V6.75z"
                      />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-semibold text-slate-700">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    className="block w-full rounded-2xl border border-slate-200 bg-slate-50/60 px-4 py-3 text-base font-medium text-slate-900 shadow-sm transition focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200 focus:ring-offset-2 focus:ring-offset-white"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute inset-y-1.5 right-1.5 inline-flex items-center rounded-xl px-3 text-xs font-semibold text-primary-600 transition hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-200"
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="group relative flex w-full items-center justify-center gap-3 rounded-2xl bg-primary-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-primary-600/30 transition hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-200 focus:ring-offset-2 focus:ring-offset-white disabled:cursor-not-allowed disabled:opacity-80"
              >
                {isLoading ? (
                  <>
                    <svg
                      className="h-5 w-5 animate-spin text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle className="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>
          </div>

          <div className="mt-8 rounded-3xl border border-primary-100/80 bg-primary-50/70 p-6 shadow-inner">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-primary-700">Demo credentials</h3>
                <p className="mt-1 text-xs text-primary-700/80">
                  Explore the workspace using any of the curated sample accounts below.
                </p>
              </div>
              <span className="rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-primary-600">
                Password: {sharedPassword}
              </span>
            </div>

            <ul className="mt-6 space-y-4">
              {demoAccounts.map((account) => (
                <li
                  key={account.email}
                  className="rounded-2xl bg-white/90 p-4 shadow-sm ring-1 ring-primary-100/70 backdrop-blur-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{account.name}</p>
                      <p className="text-xs text-slate-500">{account.focus}</p>
                      <p className="mt-1 text-xs font-medium text-slate-600">{account.email}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopyCredential(account.email)}
                      className="inline-flex items-center gap-2 rounded-xl border border-primary-200 bg-white px-3 py-1.5 text-xs font-semibold text-primary-600 transition hover:border-primary-300 hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-200"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        className="h-4 w-4"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M8.25 7.5V6A2.25 2.25 0 0110.5 3.75h7.5A2.25 2.25 0 0120.25 6v9a2.25 2.25 0 01-2.25 2.25H16.5m-4.5 0H6.75A2.25 2.25 0 014.5 15V9.75A2.25 2.25 0 016.75 7.5H12a2.25 2.25 0 012.25 2.25V15a2.25 2.25 0 01-2.25 2.25z"
                        />
                      </svg>
                      {copiedUser === account.email ? 'Copied!' : 'Copy login'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </div>
  )
}
