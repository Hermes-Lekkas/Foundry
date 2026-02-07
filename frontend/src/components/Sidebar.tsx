// THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
//
// This software is provided under a proprietary license.
// See the LICENSE file for details.

import { NavLink } from 'react-router-dom'
import { useFoundryStore } from '../stores/foundryStore'

const navItems = [
  { path: '/', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { path: '/data', label: 'Data Engine', icon: 'M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7M4 7c0-2 1-3 3-3h10c2 0 3 1 3 3M4 7h16M10 11h4' },
  { path: '/training', label: 'Training', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { path: '/eval', label: 'Evaluator', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { path: '/config', label: 'Config', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
]

export default function Sidebar() {
  const connected = useFoundryStore((s) => s.connected)

  return (
    <aside className="w-64 h-screen glass-panel rounded-none border-r border-glass-200 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-glass-200">
        <h1 className="text-xl font-bold tracking-wide">
          <span className="text-foundry-accent">&#9874;</span>{' '}
          The Foundry
        </h1>
        <p className="text-xs text-gray-500 mt-1">Local LLM Training</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-foundry-primary/20 text-foundry-primary border border-foundry-primary/30'
                  : 'text-gray-400 hover:text-white hover:bg-glass-100'
              }`
            }
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
            </svg>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Connection status */}
      <div className="p-4 border-t border-glass-200">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? 'bg-foundry-success animate-pulse' : 'bg-foundry-error'
            }`}
          />
          <span className="text-gray-500">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </aside>
  )
}
