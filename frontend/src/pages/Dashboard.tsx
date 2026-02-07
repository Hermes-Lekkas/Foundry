// THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
//
// This software is provided under a proprietary license.
// See the LICENSE file for details.

import { useEffect, useState } from 'react'
import GlassCard from '../components/GlassCard'
import LossChart from '../components/LossChart'
import VRAMGauge from '../components/VRAMGauge'
import { useFoundryStore } from '../stores/foundryStore'
import { api } from '../hooks/useApi'

export default function Dashboard() {
  const hardware = useFoundryStore((s) => s.hardware)
  const setHardware = useFoundryStore((s) => s.setHardware)
  const training = useFoundryStore((s) => s.training)
  const isTraining = useFoundryStore((s) => s.isTraining)
  const connected = useFoundryStore((s) => s.connected)

  useEffect(() => {
    api.health().then((data) => {
      setHardware({
        platform: data.platform as string,
        gpu: data.gpu as string,
        vramTotalGb: data.vram_total_gb as number,
        vramFreeGb: data.vram_free_gb as number,
        cudaAvailable: data.cuda_available as boolean,
        isWsl2: data.is_wsl2 as boolean,
        tier: data.tier as string,
        datasetNumProc: data.dataset_num_proc as number,
      })
    }).catch(() => {})
  }, [])

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">
            The Foundry — Local LLM Training Ecosystem
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`pill ${
              connected
                ? 'bg-foundry-success/10 text-foundry-success border-foundry-success/20'
                : 'bg-foundry-error/10 text-foundry-error border-foundry-error/20'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-foundry-success' : 'bg-foundry-error'}`} />
            {connected ? 'Live' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Hardware & VRAM row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title="Hardware" accent="accent">
          {hardware ? (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">GPU</span>
                <p className="text-white font-medium">{hardware.gpu}</p>
              </div>
              <div>
                <span className="text-gray-500">VRAM</span>
                <p className="text-white font-medium">{hardware.vramTotalGb} GB</p>
              </div>
              <div>
                <span className="text-gray-500">Platform</span>
                <p className="text-white font-medium">{hardware.platform}</p>
              </div>
              <div>
                <span className="text-gray-500">Tier</span>
                <p className="text-white font-medium uppercase">{hardware.tier}</p>
              </div>
              <div>
                <span className="text-gray-500">CUDA</span>
                <p className={hardware.cudaAvailable ? 'text-foundry-success' : 'text-foundry-error'}>
                  {hardware.cudaAvailable ? 'Available' : 'Not Available'}
                </p>
              </div>
              <div>
                <span className="text-gray-500">Workers</span>
                <p className="text-white font-medium">{hardware.datasetNumProc}</p>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Connecting to server...</p>
          )}
        </GlassCard>

        <GlassCard title="VRAM Usage" subtitle="Real-time GPU memory" accent="success">
          <VRAMGauge />
        </GlassCard>
      </div>

      {/* Training metrics */}
      <GlassCard
        title="Training Loss"
        subtitle={
          isTraining
            ? `Step ${training.step}/${training.totalSteps} — Epoch ${training.epoch?.toFixed(2) || '0'}`
            : 'No active training'
        }
        accent={isTraining ? 'primary' : 'accent'}
      >
        <LossChart />
      </GlassCard>

      {/* Quick stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard accent="primary">
          <div className="text-center">
            <p className="text-3xl font-bold text-foundry-primary">
              {training.step}
            </p>
            <p className="text-sm text-gray-500 mt-1">Training Steps</p>
          </div>
        </GlassCard>
        <GlassCard accent="success">
          <div className="text-center">
            <p className="text-3xl font-bold text-foundry-success">
              {training.loss?.toFixed(4) || '—'}
            </p>
            <p className="text-sm text-gray-500 mt-1">Current Loss</p>
          </div>
        </GlassCard>
        <GlassCard accent="accent">
          <div className="text-center">
            <p className="text-3xl font-bold text-foundry-accent">
              {training.elapsedSeconds > 0
                ? `${Math.floor(training.elapsedSeconds / 60)}m`
                : '—'}
            </p>
            <p className="text-sm text-gray-500 mt-1">Elapsed Time</p>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
