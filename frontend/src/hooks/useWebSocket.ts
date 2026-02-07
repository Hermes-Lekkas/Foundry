// Copyright (c) 2026 Hermes Lekkas. All rights reserved.
// PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.
// Unauthorized copying, redistribution, or commercial use is strictly prohibited.

import { useEffect, useRef } from 'react'
import { useFoundryStore } from '../stores/foundryStore'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const store = useFoundryStore()

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`

    function connect() {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        store.setConnected(true)
      }

      ws.onclose = () => {
        store.setConnected(false)
        // Reconnect after 3 seconds
        setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          handleEvent(msg)
        } catch {
          // Ignore malformed messages
        }
      }
    }

    function handleEvent(msg: { type: string; data: Record<string, unknown> }) {
      switch (msg.type) {
        case 'train.start':
          store.setIsTraining(true)
          store.updateTraining({
            totalSteps: msg.data.total_steps as number,
            step: 0,
          })
          break

        case 'train.step':
          store.updateTraining({
            step: msg.data.step as number,
            totalSteps: msg.data.total_steps as number,
            loss: msg.data.loss as number | null,
            learningRate: msg.data.learning_rate as number | null,
            epoch: msg.data.epoch as number | null,
            vramUsedMb: (msg.data.vram_used_mb as number) || 0,
            vramPeakMb: (msg.data.vram_peak_mb as number) || 0,
            elapsedSeconds: (msg.data.elapsed_seconds as number) || 0,
          })
          break

        case 'train.loss':
          store.addLossPoint(
            msg.data.step as number,
            msg.data.loss as number
          )
          break

        case 'train.complete':
          store.setIsTraining(false)
          break

        case 'vram.profile.complete':
          store.setVRAMProfile({
            safeBatchSize: msg.data.safe_batch_size as number,
            maxBatchSize: msg.data.max_batch_size as number,
            vramTotalMb: msg.data.vram_total_mb as number,
            vramCeilingMb: msg.data.vram_ceiling_mb as number,
            vramPeakMb: msg.data.vram_peak_mb as number,
          })
          break

        case 'data.synth.progress':
          store.setSynthProgress({
            current: msg.data.current as number,
            total: msg.data.total as number,
          })
          break

        case 'data.synth.complete':
          store.setSynthProgress(null)
          break
      }
    }

    connect()

    // Ping keepalive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      wsRef.current?.close()
    }
  }, [])
}
