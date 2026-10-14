import { useState } from 'react'
import { BottomSheet } from '@/components/BottomSheet'
import { Button } from '@/components/Button'
import type { NotificationStatus, RunningRestTimer } from '@/hooks/useRestTimer'
import { formatRestTime, remainingRestRatio } from '@/lib/restTimer'

type RestTimerSheetProps = {
  open: boolean
  onClose: () => void
  running: RunningRestTimer
  notificationStatus: NotificationStatus
  onExtend: () => Promise<void>
  onStop: () => Promise<boolean>
}

const CIRCLE_RADIUS = 45
const CIRCLE_LENGTH = 2 * Math.PI * CIRCLE_RADIUS

export function RestTimerSheet({ open, onClose, running, notificationStatus, onExtend, onStop }: RestTimerSheetProps) {
  const [extendPending, setExtendPending] = useState(false)

  async function extendRestTimerOnce() {
    setExtendPending(true)
    await onExtend()
    setExtendPending(false)
  }

  async function stopRestTimerAndClose() {
    if (await onStop()) onClose()
  }

  return (
    <BottomSheet open={open} onClose={onClose} title="レスト">
      <div className="flex flex-col items-center gap-6">
        {running.nextSetLabel !== '' && <p className="text-std-16N-170">次: {running.nextSetLabel}</p>}
        <div className="relative size-48">
          <svg viewBox="0 0 100 100" aria-hidden className="size-full -rotate-90">
            <circle cx="50" cy="50" r={CIRCLE_RADIUS} fill="none" strokeWidth="6" className="stroke-border" />
            <circle
              cx="50"
              cy="50"
              r={CIRCLE_RADIUS}
              fill="none"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={CIRCLE_LENGTH}
              strokeDashoffset={CIRCLE_LENGTH * (1 - remainingRestRatio(running.remainingSeconds, running.totalSeconds))}
              className="stroke-primary"
            />
          </svg>
          <p
            role="timer"
            aria-label="残り時間"
            className="absolute inset-0 flex items-center justify-center text-std-45B-140 tabular-nums"
          >
            {formatRestTime(running.remainingSeconds)}
          </p>
        </div>
        {notificationStatus === 'disabled' && (
          <p className="text-dns-14N-130 text-muted-foreground">通知はオフです。終了の通知は届きません</p>
        )}
        <div className="grid w-full grid-cols-2 gap-4">
          <Button size="lg" variant="outline" disabled={extendPending} onClick={() => void extendRestTimerOnce()}>
            +30秒
          </Button>
          <Button
            size="lg"
            variant="solid-fill"
            onClick={() => void stopRestTimerAndClose()}
          >
            停止
          </Button>
        </div>
      </div>
    </BottomSheet>
  )
}
