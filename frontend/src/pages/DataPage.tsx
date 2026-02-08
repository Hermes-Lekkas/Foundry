// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import GlassCard from '../components/GlassCard'
import { api } from '../hooks/useApi'
import { useFoundryStore } from '../stores/foundryStore'

export default function DataPage() {
  const [constitutions, setConstitutions] = useState<{ name: string; path: string }[]>([])
  const [datasets, setDatasets] = useState<Record<string, unknown>[]>([])
  const [selectedConst, setSelectedConst] = useState('agentic')
  const [pipeline, setPipeline] = useState('trajectory')
  const [numSamples, setNumSamples] = useState(100)
  const synthProgress = useFoundryStore((s) => s.synthProgress)

  useEffect(() => {
    api.listConstitutions().then(setConstitutions).catch(() => {})
    api.listDatasets().then(setDatasets).catch(() => {})
  }, [])

  const startSynth = async () => {
    try {
      const result = await api.startSynthesis({
        constitution: selectedConst,
        pipeline,
        num_samples: numSamples,
      })
      toast.success(`Synthesis started: ${result.job_id}`)
    } catch (err) {
      toast.error('Failed to start synthesis')
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Data Engine</h1>
        <p className="text-gray-500 text-sm mt-1">
          Constitutional AI synthesis with verifiable trajectories
        </p>
      </div>

      {/* Synthesis controls */}
      <GlassCard title="New Synthesis" accent="success">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Constitution</label>
            <select
              className="glass-input"
              value={selectedConst}
              onChange={(e) => setSelectedConst(e.target.value)}
            >
              {constitutions.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
              {constitutions.length === 0 && <option value="agentic">agentic</option>}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Pipeline</label>
            <select
              className="glass-input"
              value={pipeline}
              onChange={(e) => setPipeline(e.target.value)}
            >
              <option value="trajectory">Verifiable Trajectory</option>
              <option value="sl_cai">SL-CAI (Critique & Revise)</option>
              <option value="rl_cai">RL-CAI (Preference Pairs)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Samples</label>
            <input
              type="number"
              className="glass-input"
              value={numSamples}
              onChange={(e) => setNumSamples(parseInt(e.target.value) || 10)}
              min={1}
              max={10000}
            />
          </div>
        </div>

        <div className="mt-4 flex items-center gap-4">
          <button
            className="glass-button glass-button-success"
            onClick={startSynth}
            disabled={synthProgress !== null}
          >
            {synthProgress ? 'Synthesizing...' : 'Start Synthesis'}
          </button>

          {synthProgress && (
            <div className="flex items-center gap-3 text-sm">
              <div className="w-48 h-2 bg-foundry-surface rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-foundry-success to-foundry-accent rounded-full"
                  animate={{
                    width: `${(synthProgress.current / synthProgress.total) * 100}%`,
                  }}
                />
              </div>
              <span className="text-gray-400">
                {synthProgress.current}/{synthProgress.total}
              </span>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Pipeline info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            name: 'Verifiable Trajectory',
            desc: 'Teacher generates tool calls, sandbox executes them, real outputs feed back. No mock success.',
            accent: 'accent' as const,
          },
          {
            name: 'SL-CAI',
            desc: 'Generate, critique against constitutional principles, then revise. Produces refined SFT data.',
            accent: 'primary' as const,
          },
          {
            name: 'RL-CAI',
            desc: 'Generate preference pairs judged by constitutional principles. For DPO training.',
            accent: 'warning' as const,
          },
        ].map((p) => (
          <GlassCard key={p.name} title={p.name} accent={p.accent}>
            <p className="text-sm text-gray-400">{p.desc}</p>
          </GlassCard>
        ))}
      </div>

      {/* Datasets */}
      <GlassCard title="Datasets" subtitle={`${datasets.length} datasets`} accent="primary">
        {datasets.length === 0 ? (
          <p className="text-gray-500 text-sm">No datasets generated yet</p>
        ) : (
          <div className="space-y-2">
            {datasets.map((ds, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-xl bg-glass-50 border border-glass-100"
              >
                <div>
                  <p className="text-sm font-medium">{ds.name as string}</p>
                  <p className="text-xs text-gray-500">{ds.format as string}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-foundry-accent">
                    {ds.num_samples as number} samples
                  </p>
                  <p className="text-xs text-gray-500">
                    {ds.size_mb as number} MB
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
