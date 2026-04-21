'use client';

import { useState, useEffect } from 'react';

const PERIODS = [
  { label: '24 Hours', value: '24h' },
  { label: '7 Days', value: '7d' },
  { label: '30 Days', value: '30d' },
];

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('7d');
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchAnalytics() {
      try {
        setLoading(true);
        const res = await fetch(`/api/analytics?period=${period}`);
        if (!res.ok) throw new Error('Failed to fetch');
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, [period]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Privacy Analytics</h1>
            <p className="text-gray-400 mt-1">Page view statistics dashboard</p>
          </div>
          <div className="flex gap-2 bg-gray-800 p-1 rounded-lg">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  period === p.value
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 mb-6">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : data ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <p className="text-gray-400 text-sm uppercase tracking-wide">Total Page Views</p>
                <p className="text-4xl font-bold mt-2 text-white">{data.total.toLocaleString()}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <p className="text-gray-400 text-sm uppercase tracking-wide">Unique Pages</p>
                <p className="text-4xl font-bold mt-2 text-white">{data.topPages.length}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <p className="text-gray-400 text-sm uppercase tracking-wide">Referrers</p>
                <p className="text-4xl font-bold mt-2 text-white">{data.topReferrers.length}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <h2 className="text-xl font-semibold mb-4">Top Pages</h2>
                {data.topPages.length > 0 ? (
                  <div className="space-y-3">
                    {data.topPages.map((page, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-gray-300 font-mono text-sm truncate max-w-xs">{page.path}</span>
                        <span className="bg-blue-900 text-blue-300 px-3 py-1 rounded-full text-sm font-medium">
                          {page.views.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">No data available</p>
                )}
              </div>

              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <h2 className="text-xl font-semibold mb-4">Top Referrers</h2>
                {data.topReferrers.length > 0 ? (
                  <div className="space-y-3">
                    {data.topReferrers.map((ref, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-gray-300 text-sm truncate max-w-xs">{ref.referrer || 'Direct'}</span>
                        <span className="bg-purple-900 text-purple-300 px-3 py-1 rounded-full text-sm font-medium">
                          {ref.count.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">No referrer data</p>
                )}
              </div>

              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 lg:col-span-2">
                <h2 className="text-xl font-semibold mb-4">Daily Views</h2>
                {data.dailyViews.length > 0 ? (
                  <div className="flex items-end gap-2 h-48">
                    {data.dailyViews.map((day, i) => {
                      const maxViews = Math.max(...data.dailyViews.map(d => d.views));
                      const height = maxViews > 0 ? (day.views / maxViews) * 100 : 0;
                      return (
                        <div key={i} className="flex-1 flex flex-col items-center gap-2">
                          <div className="w-full bg-blue-600 rounded-t-md transition-all" style={{ height: `${height}%`, minHeight: height > 0 ? '4px' : '0' }}></div>
                          <span className="text-xs text-gray-500">{new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                          <span className="text-xs text-gray-400">{day.views}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-gray-500">No daily data available</p>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
            <p className="text-gray-400">No analytics data yet</p>
          </div>
        )}
      </div>
    </div>
  );
}