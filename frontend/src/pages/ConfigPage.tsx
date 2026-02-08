// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { useEffect, useState } from 'react'
import GlassCard from '../components/GlassCard'
import { api } from '../hooks/useApi'
import { useFoundryStore } from '../stores/foundryStore'

export default function ConfigPage() {
  const hardware = useFoundryStore((s) => s.hardware)
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null)
  const [tiers, setTiers] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => {})
    api.getTiers().then(setTiers).catch(() => {})
  }, [])

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Configuration</h1>
        <p className="text-gray-500 text-sm mt-1">
          Hardware profiles, tier configs, and system settings
        </p>
      </div>

      {/* Current Settings */}
      <GlassCard title="Current Settings" accent="primary">
        {settings ? (
          <div className="grid grid-cols-2 gap-4 text-sm">
            {Object.entries(settings).map(([key, value]) => (
              <div key={key}>
                <span className="text-gray-500">{key}</span>
                <p className="text-white font-mono text-xs mt-0.5">
                  {String(value)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Loading...</p>
        )}
      </GlassCard>

      {/* Hardware Tiers */}
      <GlassCard title="Hardware Tiers" subtitle="Recommended configs by VRAM" accent="accent">
        {tiers ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(tiers).map(([tier, config]) => {
              const c = config as Record<string, unknown>
              const isActive = hardware?.tier === tier
              return (
                <div
                  key={tier}
                  className={`p-4 rounded-xl border ${
                    isActive
                      ? 'border-foundry-primary/50 bg-foundry-primary/5'
                      : 'border-glass-100 bg-glass-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-white uppercase">{tier}</h4>
                    {isActive && (
                      <span className="pill bg-foundry-primary/20 text-foundry-primary border-foundry-primary/30 text-xs">
                        Active
                      </span>
                    )}
                  </div>
                  <div className="space-y-1 text-xs text-gray-400">
                    <p>Max params: {c.max_model_params as string}</p>
                    <p>Quantization: {c.quantization as string}</p>
                    <p>Max seq: {c.max_seq_len as number}</p>
                    <p>Batch hint: {c.batch_size_hint as number}</p>
                    <div className="mt-2">
                      <p className="text-gray-500">Recommended models:</p>
                      {(c.recommended_models as string[]).map((m) => (
                        <p key={m} className="text-foundry-accent font-mono text-xs">
                          {m}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Loading...</p>
        )}
      </GlassCard>

      {/* Environment info */}
      {hardware && !hardware.cudaAvailable && (
        <GlassCard title="Warning" accent="warning">
          <p className="text-foundry-warning text-sm">
            No CUDA GPU detected. Training will be extremely slow on CPU.
            Ensure you have an NVIDIA GPU with proper CUDA drivers installed.
          </p>
        </GlassCard>
      )}

      {hardware && hardware.platform === 'windows_native' && (
        <GlassCard title="WSL2 Recommended" accent="warning">
          <p className="text-foundry-warning text-sm">
            Running on native Windows limits multiprocessing (dataset_num_proc=1).
            Install WSL2 for full performance:{' '}
            <code className="bg-glass-100 px-1.5 py-0.5 rounded text-xs">
              wsl --install
            </code>
          </p>
        </GlassCard>
      )}
    </div>
  )
}
