'use client'

import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { QueueDepthSample } from '@qa-dashboard/shared'

interface QueueDepthCardProps {
  data: QueueDepthSample[]
}

export function QueueDepthCard({ data }: QueueDepthCardProps) {
  const chartData = data
    .slice()
    .reverse()
    .map((sample) => ({
      time: new Date(sample.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      depth: sample.depth,
    }))

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-700">Offline queue</h3>
      <p className="text-xs text-slate-500">Last hour</p>
      <div className="mt-4 h-40">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <XAxis dataKey="time" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} width={24} />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Line type="monotone" dataKey="depth" stroke="#2563eb" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
