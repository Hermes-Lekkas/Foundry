// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
// PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.
// Unauthorized copying, redistribution, or commercial use is strictly prohibited.

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

export const api = {
  // Health
  health: () => request<Record<string, unknown>>('/health'),

  // Config
  getHardware: () => request<Record<string, unknown>>('/config/hardware'),
  getSettings: () => request<Record<string, unknown>>('/config/settings'),
  getTiers: () => request<Record<string, unknown>>('/config/tiers'),

  // Data
  startSynthesis: (body: Record<string, unknown>) =>
    request<{ job_id: string }>('/data/synthesize', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listDataJobs: () => request<Record<string, unknown>[]>('/data/jobs'),
  listDatasets: () => request<Record<string, unknown>[]>('/data/datasets'),
  listConstitutions: () =>
    request<{ name: string; path: string }[]>('/data/constitutions'),

  // Training
  startTraining: (body: Record<string, unknown>) =>
    request<{ job_id: string }>('/training/start', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listTrainingJobs: () =>
    request<Record<string, unknown>[]>('/training/jobs'),
  stopTraining: (jobId: string) =>
    request<Record<string, unknown>>(`/training/jobs/${jobId}/stop`, {
      method: 'POST',
    }),
  profileVRAM: (modelName: string) =>
    request<Record<string, unknown>>(
      `/training/profile?model_name=${encodeURIComponent(modelName)}`,
      { method: 'POST' }
    ),

  // Eval
  startEval: (body: Record<string, unknown>) =>
    request<{ job_id: string }>('/eval/run', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listEvalJobs: () => request<Record<string, unknown>[]>('/eval/jobs'),
  getLeaderboard: () => request<Record<string, unknown>[]>('/eval/leaderboard'),
}
