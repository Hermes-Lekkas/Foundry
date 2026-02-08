// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { motion } from 'framer-motion'
import { useFoundryStore } from '../stores/foundryStore'

export default function VRAMGauge() {
  const training = useFoundryStore((s) => s.training)
  const vramProfile = useFoundryStore((s) => s.vramProfile)

  const totalMb = vramProfile?.vramTotalMb || 24576 // Fallback 24GB
  const usedMb = training.vramUsedMb
  const peakMb = training.vramPeakMb
  const ceilingMb = vramProfile?.vramCeilingMb || totalMb * 0.9

  const usedPct = (usedMb / totalMb) * 100
  const ceilingPct = (ceilingMb / totalMb) * 100
  const peakPct = (peakMb / totalMb) * 100

  const getColor = () => {
    if (usedPct > 90) return 'from-foundry-error to-red-400'
    if (usedPct > 70) return 'from-foundry-warning to-amber-400'
    return 'from-foundry-success to-foundry-accent'
  }

  return (
    <div className="space-y-3">
      {/* Bar */}
      <div className="relative h-6 bg-foundry-surface rounded-full overflow-hidden">
        {/* Ceiling line */}
        <div
          className="absolute top-0 bottom-0 w-px bg-foundry-warning/50 z-10"
          style={{ left: `${ceilingPct}%` }}
        />
        <div
          className="absolute -top-5 text-[10px] text-foundry-warning/70 whitespace-nowrap"
          style={{ left: `${ceilingPct}%`, transform: 'translateX(-50%)' }}
        >
          90% ceiling
        </div>

        {/* Peak indicator */}
        {peakMb > 0 && (
          <div
            className="absolute top-0 bottom-0 w-px bg-foundry-error/40 z-10"
            style={{ left: `${peakPct}%` }}
          />
        )}

        {/* Usage bar */}
        <motion.div
          className={`h-full bg-gradient-to-r ${getColor()} rounded-full`}
          animate={{ width: `${usedPct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between text-xs text-gray-500">
        <span>{(usedMb / 1024).toFixed(1)} GB used</span>
        <span>{(totalMb / 1024).toFixed(1)} GB total</span>
      </div>

      {/* Profile info */}
      {vramProfile && (
        <div className="flex gap-4 text-xs text-gray-500">
          <span>
            Safe batch: <span className="text-foundry-accent">{vramProfile.safeBatchSize}</span>
          </span>
          <span>
            Max batch: <span className="text-gray-400">{vramProfile.maxBatchSize}</span>
          </span>
        </div>
      )}
    </div>
  )
}
