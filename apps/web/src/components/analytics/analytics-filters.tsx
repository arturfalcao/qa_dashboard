'use client'

interface AnalyticsFiltersProps {
  range: 'last_7d' | 'last_30d'
  setRange: (range: 'last_7d' | 'last_30d') => void
  groupBy: 'style' | 'factory'
  setGroupBy: (groupBy: 'style' | 'factory') => void
}

export function AnalyticsFilters({ range, setRange, groupBy, setGroupBy }: AnalyticsFiltersProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Time Range
          </label>
          <select
            value={range}
            onChange={(e) => setRange(e.target.value as 'last_7d' | 'last_30d')}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          >
            <option value="last_7d">Last 7 Days</option>
            <option value="last_30d">Last 30 Days</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Group By
          </label>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as 'style' | 'factory')}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          >
            <option value="factory">Factory</option>
            <option value="style">Style</option>
          </select>
        </div>
      </div>
    </div>
  )
}
