import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { restTimerApi } from '@/api/fetcher'

type RestTimerResponse = Awaited<ReturnType<typeof restTimerApi.start>>

export type NotificationStatus = 'enabled' | 'disabled'

export type RunningRestTimer = {
  remainingSeconds: number
  totalSeconds: number
  nextSetLabel: string
}

export type RestTimerControls = {
  running: RunningRestTimer | null
  notificationStatus: NotificationStatus
  startRestTimer: (seconds: number, nextSetLabel: string) => Promise<void>
  extendRestTimer: () => Promise<void>
  stopRestTimer: () => Promise<void>
}

const EXTEND_SECONDS = 30

function isPushSupported(): boolean {
  return 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window
}

function readNotificationStatus(): NotificationStatus {
  return isPushSupported() && Notification.permission === 'granted' ? 'enabled' : 'disabled'
}

// iOS は利用者の操作の中でないと許可を求められないため、requestPermission を最初の await より前に呼ぶ
async function enableNotification(): Promise<NotificationStatus> {
  if (!isPushSupported()) return 'disabled'
  if ((await Notification.requestPermission()) !== 'granted') return 'disabled'
  const registration = await navigator.serviceWorker.ready
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: import.meta.env.VITE_VAPID_PUBLIC_KEY,
    }))
  const { keys } = subscription.toJSON()
  if (keys === undefined) return 'disabled'
  await restTimerApi.subscribe({ endpoint: subscription.endpoint, p256dh: keys.p256dh, auth: keys.auth })
  return 'enabled'
}

export function useRestTimer(): RestTimerControls {
  const [timer, setTimer] = useState<RestTimerResponse | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const [notificationStatus, setNotificationStatus] = useState(readNotificationStatus)
  const notificationRequested = useRef(false)

  function showTimer(next: RestTimerResponse | null) {
    setNow(Date.now())
    setTimer(next)
  }

  useEffect(() => {
    let cancelled = false
    restTimerApi
      .get()
      .then((loaded) => {
        if (cancelled) return
        setNow(Date.now())
        setTimer((current) => current ?? loaded)
      })
      .catch(() => !cancelled && toast.error('レストタイマーを取得できませんでした'))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (timer === null) return
    const endsAt = Date.parse(timer.ends_at)
    const intervalId = setInterval(() => {
      const current = Date.now()
      setNow(current)
      if (current >= endsAt) setTimer(null)
    }, 1000)
    return () => clearInterval(intervalId)
  }, [timer])

  async function startRestTimer(seconds: number, nextSetLabel: string) {
    if (!notificationRequested.current) {
      notificationRequested.current = true
      enableNotification()
        .then(setNotificationStatus)
        .catch(() => setNotificationStatus('disabled'))
    }
    try {
      showTimer(await restTimerApi.start({ seconds, next_set_label: nextSetLabel }))
    } catch {
      toast.error('レストタイマーを開始できませんでした')
    }
  }

  async function extendRestTimer() {
    try {
      showTimer(await restTimerApi.extend({ seconds: EXTEND_SECONDS }))
    } catch {
      toast.error('レストタイマーを延長できませんでした')
    }
  }

  async function stopRestTimer() {
    try {
      await restTimerApi.stop()
      showTimer(null)
    } catch {
      toast.error('レストタイマーを停止できませんでした')
    }
  }

  return {
    running:
      timer === null
        ? null
        : {
            remainingSeconds: Math.max(0, Math.ceil((Date.parse(timer.ends_at) - now) / 1000)),
            totalSeconds: timer.total_seconds,
            nextSetLabel: timer.next_set_label,
          },
    notificationStatus,
    startRestTimer,
    extendRestTimer,
    stopRestTimer,
  }
}
