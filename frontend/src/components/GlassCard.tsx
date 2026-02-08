// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

interface GlassCardProps {
  title?: string
  subtitle?: string
  children: ReactNode
  className?: string
  accent?: 'primary' | 'success' | 'warning' | 'error' | 'accent'
}

const accentColors = {
  primary: 'from-foundry-primary/20 to-transparent border-foundry-primary/20',
  success: 'from-foundry-success/20 to-transparent border-foundry-success/20',
  warning: 'from-foundry-warning/20 to-transparent border-foundry-warning/20',
  error: 'from-foundry-error/20 to-transparent border-foundry-error/20',
  accent: 'from-foundry-accent/20 to-transparent border-foundry-accent/20',
}

export default function GlassCard({
  title,
  subtitle,
  children,
  className = '',
  accent = 'primary',
}: GlassCardProps) {
  return (
    <motion.div
      className={`glass-panel p-6 ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
    >
      {/* Accent glow */}
      <div
        className={`absolute top-0 left-0 right-0 h-px bg-gradient-to-r ${accentColors[accent]}`}
      />

      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-lg font-semibold text-white">{title}</h3>
          )}
          {subtitle && (
            <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
          )}
        </div>
      )}
      {children}
    </motion.div>
  )
}
