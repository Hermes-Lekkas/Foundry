// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { useState } from 'react'
import toast from 'react-hot-toast'
import GlassCard from '../components/GlassCard'
import LossChart from '../components/LossChart'
import VRAMGauge from '../components/VRAMGauge'
import { api } from '../hooks/useApi'
import { useFoundryStore } from '../stores/foundryStore'

export default function TrainingPage() {
  const isTraining = useFoundryStore((s) => s.isTraining)
  const training = useFoundryStore((s) => s.training)
  const hardware = useFoundryStore((s) => s.hardware)

  const [modelName, setModelName] = useState('unsloth/Qwen2.5-0.5B')
  const [trainerType, setTrainerType] = useState('sft')
  const [datasetPath, setDatasetPath] = useState('')
  const [numEpochs, setNumEpochs] = useState(3)
  const [learningRate, setLearningRate] = useState(2e-4)
  const [maxSeqLength, setMaxSeqLength] = useState(2048)
  const [quantization, setQuantization] = useState('4bit-nf4')
  const [loraR, setLoraR] = useState(16)

  const startTraining = async () => {
    try {
      const result = await api.startTraining({
        model_name: modelName,
        trainer_type: trainerType,
        dataset_path: datasetPath || undefined,
        num_epochs: numEpochs,
        learning_rate: learningRate,
        max_seq_length: maxSeqLength,
        quantization,
        lora_r: loraR,
        lora_alpha: loraR,
      })
      toast.success(`Training started: ${result.job_id}`)
    } catch (err) {
      toast.error('Failed to start training')
    }
  }

  const profileVRAM = async () => {
    try {
      toast.loading('Profiling VRAM...')
      const result = await api.profileVRAM(modelName)
      toast.dismiss()
      toast.success(
        `Safe batch: ${result.safe_batch_size}, Max: ${result.max_batch_size}`
      )
    } catch {
      toast.dismiss()
      toast.error('VRAM profiling failed')
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Training Core</h1>
        <p className="text-gray-500 text-sm mt-1">
          Muon-AdamW hybrid optimizer with GRPO reasoning verification
        </p>
      </div>

      {/* Config */}
      <GlassCard title="Training Configuration" accent="primary">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Model</label>
            <input
              className="glass-input"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="unsloth/Qwen2.5-0.5B"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Trainer</label>
            <select
              className="glass-input"
              value={trainerType}
              onChange={(e) => setTrainerType(e.target.value)}
            >
              <option value="sft">SFT (Supervised Fine-Tuning)</option>
              <option value="dpo">DPO (Direct Preference)</option>
              <option value="grpo">GRPO (Group Relative Policy)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Dataset Path</label>
            <input
              className="glass-input"
              value={datasetPath}
              onChange={(e) => setDatasetPath(e.target.value)}
              placeholder="./datasets/generated/..."
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Epochs</label>
            <input
              type="number"
              className="glass-input"
              value={numEpochs}
              onChange={(e) => setNumEpochs(parseInt(e.target.value) || 1)}
              min={1}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Learning Rate</label>
            <input
              className="glass-input"
              value={learningRate}
              onChange={(e) => setLearningRate(parseFloat(e.target.value) || 2e-4)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Max Seq Length</label>
            <select
              className="glass-input"
              value={maxSeqLength}
              onChange={(e) => setMaxSeqLength(parseInt(e.target.value))}
            >
              <option value={512}>512</option>
              <option value={1024}>1024</option>
              <option value={2048}>2048</option>
              <option value={4096}>4096</option>
              <option value={8192}>8192</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Quantization</label>
            <select
              className="glass-input"
              value={quantization}
              onChange={(e) => setQuantization(e.target.value)}
            >
              <option value="4bit-nf4">4-bit NF4 (QLoRA)</option>
              <option value="8bit">8-bit</option>
              <option value="none">None (Full Precision)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">LoRA Rank</label>
            <select
              className="glass-input"
              value={loraR}
              onChange={(e) => setLoraR(parseInt(e.target.value))}
            >
              <option value={8}>8 (Low VRAM)</option>
              <option value={16}>16 (Standard)</option>
              <option value={32}>32 (High Quality)</option>
              <option value={64}>64 (Maximum)</option>
            </select>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            className="glass-button glass-button-success"
            onClick={startTraining}
            disabled={isTraining}
          >
            {isTraining ? 'Training in Progress...' : 'Start Training'}
          </button>
          <button className="glass-button" onClick={profileVRAM}>
            Profile VRAM
          </button>
        </div>
      </GlassCard>

      {/* Live metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <GlassCard
            title="Loss Curve"
            subtitle={isTraining ? `Step ${training.step}/${training.totalSteps}` : 'Idle'}
            accent={isTraining ? 'primary' : 'accent'}
          >
            <LossChart />
          </GlassCard>
        </div>
        <div className="space-y-6">
          <GlassCard title="VRAM" accent="success">
            <VRAMGauge />
          </GlassCard>
          <GlassCard title="Metrics" accent="accent">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Loss</span>
                <span className="text-white font-mono">
                  {training.loss?.toFixed(4) || '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">LR</span>
                <span className="text-white font-mono">
                  {training.learningRate?.toExponential(2) || '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Epoch</span>
                <span className="text-white font-mono">
                  {training.epoch?.toFixed(2) || '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Elapsed</span>
                <span className="text-white font-mono">
                  {training.elapsedSeconds > 0
                    ? `${Math.floor(training.elapsedSeconds / 60)}m ${Math.floor(training.elapsedSeconds % 60)}s`
                    : '—'}
                </span>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
