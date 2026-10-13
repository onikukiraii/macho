import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { toast } from 'sonner'
import type { RestTimerResponse } from '@/api/constants'
import { restTimerApi } from '@/api/fetcher'
import { remainingRestSeconds } from '@/lib/restTimer'

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
  /** 停止できたら true を返す */
  stopRestTimer: () => Promise<boolean>
}

type ShownRestTimer = {
  response: RestTimerResponse
  /** 端末の時計からサーバーの時計を引いた差 */
  clockOffsetMs: number
}

const EXTEND_SECONDS = 30

function isPushSupported(): boolean {
  return 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window
}

function readNotificationStatus(): NotificationStatus {
  return isPushSupported() && Notification.permission === 'granted' ? 'enabled' : 'disabled'
}

function decodeBase64Url(value: string): Uint8Array<ArrayBuffer> {
  return Uint8Array.from(atob(value.replaceAll('-', '+').replaceAll('_', '/')), (char) => char.charCodeAt(0))
}

function hasApplicationServerKey(subscription: PushSubscription, applicationServerKey: Uint8Array): boolean {
  if (subscription.options.applicationServerKey === null) return false
  const subscribedKey = new Uint8Array(subscription.options.applicationServerKey)
  return (
    subscribedKey.length === applicationServerKey.length &&
    subscribedKey.every((byte, index) => byte === applicationServerKey[index])
  )
}

// VAPID の鍵を変えたあとも古い鍵の購読が残り、その購読へは送れないため作り直す
async function subscribePush(pushManager: PushManager): Promise<PushSubscription> {
  const applicationServerKey = decodeBase64Url(import.meta.env.VITE_VAPID_PUBLIC_KEY)
  const subscription = await pushManager.getSubscription()
  if (subscription !== null && hasApplicationServerKey(subscription, applicationServerKey)) return subscription
  await subscription?.unsubscribe()
  return pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })
}

// iOS は利用者の操作の中でないと許可を求められないため、requestPermission を最初の await より前に呼ぶ
async function enableNotification(): Promise<NotificationStatus> {
  if (!isPushSupported()) return 'disabled'
  if ((await Notification.requestPermission()) !== 'granted') return 'disabled'
  const registration = await navigator.serviceWorker.ready
  const subscription = await subscribePush(registration.pushManager)
  const { keys } = subscription.toJSON()
  if (keys === undefined) return 'disabled'
  await restTimerApi.subscribe({ endpoint: subscription.endpoint, p256dh: keys.p256dh, auth: keys.auth })
  return 'enabled'
}

/** 操作の連番を進め、その操作がまだ最新かを返す関数を返す。後から届いた古い応答で表示を戻さないため */
function beginRestTimerRequest(latestRequestId: RefObject<number>): () => boolean {
  latestRequestId.current += 1
  const requestId = latestRequestId.current
  return () => requestId === latestRequestId.current
}

export function useRestTimer(): RestTimerControls {
  const [timer, setTimer] = useState<ShownRestTimer | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const [notificationStatus, setNotificationStatus] = useState(readNotificationStatus)
  const notificationRequested = useRef(false)
  const latestRequestId = useRef(0)

  const loadRestTimer = useCallback(() => restTimerApi.get(), [])

  useEffect(() => {
    const isLatestRequest = beginRestTimerRequest(latestRequestId)
    loadRestTimer()
      .then((loaded) => {
        if (!isLatestRequest()) return
        setNow(Date.now())
        // 取得の応答からは時計の差を求められないため、端末の時計で数える
        setTimer(loaded === null ? null : { response: loaded, clockOffsetMs: 0 })
      })
      .catch(() => isLatestRequest() && toast.error('レストタイマーを取得できませんでした'))
  }, [loadRestTimer])

  useEffect(() => {
    if (timer === null) return
    const endsAtMs = Date.parse(timer.response.ends_at) + timer.clockOffsetMs
    const intervalId = setInterval(() => {
      const current = Date.now()
      setNow(current)
      if (current >= endsAtMs) setTimer(null)
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
    const isLatestRequest = beginRestTimerRequest(latestRequestId)
    try {
      const started = await restTimerApi.start({ seconds, next_set_label: nextSetLabel })
      if (!isLatestRequest()) return
      const receivedAtMs = Date.now()
      setNow(receivedAtMs)
      // サーバーが開始した時刻を、端末が応答を受け取った時刻とみなす
      setTimer({ response: started, clockOffsetMs: receivedAtMs - Date.parse(started.started_at) })
    } catch {
      if (isLatestRequest()) toast.error('レストタイマーを開始できませんでした')
    }
  }

  async function extendRestTimer() {
    const isLatestRequest = beginRestTimerRequest(latestRequestId)
    try {
      const extended = await restTimerApi.extend({ seconds: EXTEND_SECONDS })
      if (!isLatestRequest()) return
      setNow(Date.now())
      setTimer((current) => ({ response: extended, clockOffsetMs: current?.clockOffsetMs ?? 0 }))
    } catch {
      if (isLatestRequest()) toast.error('レストタイマーを延長できませんでした')
    }
  }

  async function stopRestTimer() {
    const isLatestRequest = beginRestTimerRequest(latestRequestId)
    try {
      await restTimerApi.stop()
      if (!isLatestRequest()) return false
      setTimer(null)
      return true
    } catch {
      if (isLatestRequest()) toast.error('レストタイマーを停止できませんでした')
      return false
    }
  }

  return {
    running:
      timer === null
        ? null
        : {
            remainingSeconds: remainingRestSeconds(
              Date.parse(timer.response.ends_at) + timer.clockOffsetMs,
              now,
              timer.response.total_seconds,
            ),
            totalSeconds: timer.response.total_seconds,
            nextSetLabel: timer.response.next_set_label,
          },
    notificationStatus,
    startRestTimer,
    extendRestTimer,
    stopRestTimer,
  }
}
