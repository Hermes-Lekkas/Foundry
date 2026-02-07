// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
// PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.
// Unauthorized copying, redistribution, or commercial use is strictly prohibited.

import { create } from 'zustand'

interface TrainingMetrics {
  step: number
  totalSteps: number
  loss: number | null
  learningRate: number | null
  epoch: number | null
  vramUsedMb: number
  vramPeakMb: number
  elapsedSeconds: number
}

interface VRAMProfile {
  safeBatchSize: number
  maxBatchSize: number
  vramTotalMb: number
  vramCeilingMb: number
  vramPeakMb: number
}

interface Job {
  id: string
  type: string
  status: string
  config?: Record<string, unknown>
  result?: Record<string, unknown>
  error?: string
  created_at: string
}

interface HardwareInfo {
  platform: string
  gpu: string
  vramTotalGb: number
  vramFreeGb: number
  cudaAvailable: boolean
  isWsl2: boolean
  tier: string
  datasetNumProc: number
}

interface FoundryState {
  // Connection
  connected: boolean
  setConnected: (v: boolean) => void

  // Hardware
  hardware: HardwareInfo | null
  setHardware: (hw: HardwareInfo) => void

  // Training
  training: TrainingMetrics
  lossHistory: { step: number; loss: number }[]
  isTraining: boolean
  updateTraining: (metrics: Partial<TrainingMetrics>) => void
  addLossPoint: (step: number, loss: number) => void
  setIsTraining: (v: boolean) => void

  // VRAM Profile
  vramProfile: VRAMProfile | null
  setVRAMProfile: (p: VRAMProfile) => void

  // Jobs
  jobs: Job[]
  setJobs: (jobs: Job[]) => void
  addJob: (job: Job) => void
  updateJobStatus: (id: string, status: string) => void

  // Active view
  activeView: string
  setActiveView: (v: string) => void

  // Data synthesis progress
  synthProgress: { current: number; total: number } | null
  setSynthProgress: (p: { current: number; total: number } | null) => void
}

export const useFoundryStore = create<FoundryState>((set) => ({
  connected: false,
  setConnected: (connected) => set({ connected }),

  hardware: null,
  setHardware: (hardware) => set({ hardware }),

  training: {
    step: 0,
    totalSteps: 0,
    loss: null,
    learningRate: null,
    epoch: null,
    vramUsedMb: 0,
    vramPeakMb: 0,
    elapsedSeconds: 0,
  },
  lossHistory: [],
  isTraining: false,
  updateTraining: (metrics) =>
    set((s) => ({ training: { ...s.training, ...metrics } })),
  addLossPoint: (step, loss) =>
    set((s) => ({
      lossHistory: [...s.lossHistory.slice(-500), { step, loss }],
    })),
  setIsTraining: (isTraining) => set({ isTraining }),

  vramProfile: null,
  setVRAMProfile: (vramProfile) => set({ vramProfile }),

  jobs: [],
  setJobs: (jobs) => set({ jobs }),
  addJob: (job) => set((s) => ({ jobs: [job, ...s.jobs] })),
  updateJobStatus: (id, status) =>
    set((s) => ({
      jobs: s.jobs.map((j) => (j.id === id ? { ...j, status } : j)),
    })),

  activeView: 'dashboard',
  setActiveView: (activeView) => set({ activeView }),

  synthProgress: null,
  setSynthProgress: (synthProgress) => set({ synthProgress }),
}))
