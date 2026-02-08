// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import GlassCard from '../components/GlassCard'
import { api } from '../hooks/useApi'

export default function EvalPage() {
  const [modelPath, setModelPath] = useState('./checkpoints/sft')
  const [benchmark, setBenchmark] = useState('all')
  const [judgeType, setJudgeType] = useState('prometheus')
  const [leaderboard, setLeaderboard] = useState<Record<string, unknown>[]>([])

  useEffect(() => {
    api.getLeaderboard().then(setLeaderboard).catch(() => {})
  }, [])

  const runEval = async () => {
    try {
      const result = await api.startEval({
        model_path: modelPath,
        benchmark,
        judge_type: judgeType,
      })
      toast.success(`Evaluation started: ${result.job_id}`)
    } catch {
      toast.error('Failed to start evaluation')
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Evaluator</h1>
        <p className="text-gray-500 text-sm mt-1">
          Prometheus Judge, benchmarks, and model leaderboard
        </p>
      </div>

      {/* Eval config */}
      <GlassCard title="Run Evaluation" accent="warning">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Model Path</label>
            <input
              className="glass-input"
              value={modelPath}
              onChange={(e) => setModelPath(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Benchmark</label>
            <select
              className="glass-input"
              value={benchmark}
              onChange={(e) => setBenchmark(e.target.value)}
            >
              <option value="all">All</option>
              <option value="gsm8k_sample">GSM8K (Sample)</option>
              <option value="code_quality">Code Quality</option>
              <option value="tool_use">Tool Use</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Judge</label>
            <select
              className="glass-input"
              value={judgeType}
              onChange={(e) => setJudgeType(e.target.value)}
            >
              <option value="prometheus">Prometheus 2</option>
              <option value="llm">LLM-as-Judge</option>
              <option value="rule">Rule-based</option>
            </select>
          </div>
        </div>
        <div className="mt-4">
          <button className="glass-button" onClick={runEval}>
            Run Evaluation
          </button>
        </div>
      </GlassCard>

      {/* Leaderboard */}
      <GlassCard title="Model Leaderboard" accent="accent">
        {leaderboard.length === 0 ? (
          <p className="text-gray-500 text-sm">No evaluation results yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-glass-200">
                  <th className="text-left py-3 px-2 text-gray-500 font-medium">Rank</th>
                  <th className="text-left py-3 px-2 text-gray-500 font-medium">Model</th>
                  <th className="text-right py-3 px-2 text-gray-500 font-medium">Avg Score</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((entry, i) => (
                  <tr key={i} className="border-b border-glass-100">
                    <td className="py-3 px-2">
                      <span className={`pill ${i === 0 ? 'bg-foundry-warning/20 text-foundry-warning border-foundry-warning/30' : 'bg-glass-50 text-gray-400 border-glass-100'}`}>
                        #{i + 1}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-white font-medium">
                      {(entry.model as string).split('/').pop()}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <span className="text-foundry-accent font-mono">
                        {((entry.avg_score as number) * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  )
}
