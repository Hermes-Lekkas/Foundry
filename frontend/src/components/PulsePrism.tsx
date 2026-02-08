// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { motion, AnimatePresence } from 'framer-motion'
import { useFoundryStore } from '../stores/foundryStore'

export default function PulsePrism() {
  const isTraining = useFoundryStore((s) => s.isTraining)
  const training = useFoundryStore((s) => s.training)
  const synthProgress = useFoundryStore((s) => s.synthProgress)

  const active = isTraining || synthProgress !== null

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          className="pulse-prism"
          initial={{ y: -60, opacity: 0, scale: 0.8 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          exit={{ y: -60, opacity: 0, scale: 0.8 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          {/* Glow effect */}
          <div className="absolute inset-0 rounded-full bg-foundry-primary/10 animate-pulse-glow" />

          {/* Spinner */}
          <div className="relative">
            <svg className="w-5 h-5 animate-spin text-foundry-accent" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4" fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          </div>

          {/* Content */}
          <div className="relative">
            {isTraining && (
              <div className="flex items-center gap-4">
                <span className="text-white font-medium">Training</span>
                <span className="text-foundry-accent">
                  Step {training.step}/{training.totalSteps}
                </span>
                {training.loss !== null && (
                  <span className="text-gray-400">
                    Loss: {training.loss.toFixed(4)}
                  </span>
                )}
                <div className="w-32 h-1.5 bg-foundry-surface rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-foundry-primary to-foundry-accent rounded-full"
                    animate={{
                      width: `${training.totalSteps > 0
                        ? (training.step / training.totalSteps) * 100
                        : 0}%`,
                    }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}
            {synthProgress && (
              <div className="flex items-center gap-4">
                <span className="text-white font-medium">Synthesizing</span>
                <span className="text-foundry-accent">
                  {synthProgress.current}/{synthProgress.total}
                </span>
                <div className="w-32 h-1.5 bg-foundry-surface rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-foundry-success to-foundry-accent rounded-full"
                    animate={{
                      width: `${(synthProgress.current / synthProgress.total) * 100}%`,
                    }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
