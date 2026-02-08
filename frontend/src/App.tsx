// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import PulsePrism from './components/PulsePrism'
import Dashboard from './pages/Dashboard'
import DataPage from './pages/DataPage'
import TrainingPage from './pages/TrainingPage'
import EvalPage from './pages/EvalPage'
import ConfigPage from './pages/ConfigPage'
import { useWebSocket } from './hooks/useWebSocket'

export default function App() {
  useWebSocket()

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <PulsePrism />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="/training" element={<TrainingPage />} />
          <Route path="/eval" element={<EvalPage />} />
          <Route path="/config" element={<ConfigPage />} />
        </Routes>
      </main>
      <Toaster
        position="bottom-right"
        toastOptions={{
          className: 'glass-panel text-white text-sm',
          style: {
            background: 'rgba(30, 41, 59, 0.95)',
            color: '#fff',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          },
        }}
      />
    </div>
  )
}
