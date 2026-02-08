// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

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

  // Models
  getModelCatalog: (params?: { size?: string; tag?: string; search?: string }) => {
    const query = params ? new URLSearchParams(params).toString() : ''
    return request<Record<string, unknown>[]>(`/models/catalog${query ? '?' + query : ''}`)
  },
  getModelDetails: (modelId: string) =>
    request<Record<string, unknown>>(`/models/catalog/${encodeURIComponent(modelId)}`),
  downloadModel: (modelId: string) =>
    request<{ job_id: string; status: string; message: string }>('/models/download', {
      method: 'POST',
      body: JSON.stringify({ model_id: modelId }),
    }),
  getDownloadedModels: () => request<Record<string, unknown>[]>('/models/downloaded'),
  getModelSizes: () => request<Record<string, unknown>[]>('/models/sizes'),
  getModelTags: () => request<string[]>('/models/tags'),

  // Keys / BYOK
  getKeyStatus: () => request<Record<string, unknown>[]>('/keys/status'),
  getTeacherProviders: () => request<Record<string, unknown>[]>('/keys/providers'),
  getCurrentTeacher: () => request<Record<string, unknown>>('/keys/teacher/current'),
  configureTeacher: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>('/keys/teacher/configure', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  testTeacher: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>('/keys/teacher/test', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getCurrentStudent: () => request<Record<string, unknown>>('/keys/student/current'),
  configureStudent: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>('/keys/student/configure', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  setHuggingFaceToken: (token: string) =>
    request<Record<string, unknown>>('/keys/huggingface/token', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }),

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
