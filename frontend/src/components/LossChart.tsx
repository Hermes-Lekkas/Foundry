// THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
//
// This software is provided under a proprietary license.
// See the LICENSE file for details.

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { useFoundryStore } from '../stores/foundryStore'

export default function LossChart() {
  const lossHistory = useFoundryStore((s) => s.lossHistory)

  if (lossHistory.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        Training metrics will appear here
      </div>
    )
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={lossHistory}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.05)"
          />
          <XAxis
            dataKey="step"
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11 }}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(15, 23, 42, 0.95)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '12px',
              backdropFilter: 'blur(20px)',
            }}
            labelStyle={{ color: '#94a3b8' }}
            itemStyle={{ color: '#6366f1' }}
          />
          <Line
            type="monotone"
            dataKey="loss"
            stroke="url(#lossGradient)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#6366f1' }}
          />
          <defs>
            <linearGradient id="lossGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
          </defs>
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
