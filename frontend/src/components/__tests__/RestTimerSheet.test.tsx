import { useState } from 'react'
import { act, fireEvent } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { restTimerApi } from '@/api/fetcher'
import type { RestTimerResponse } from '@/api/constants'
import { RestTimerBadge } from '@/components/RestTimerBadge'
import { RestTimerSheet } from '@/components/RestTimerSheet'
import { Toaster } from '@/components/ui/sonner'
import { useRestTimer } from '@/hooks/useRestTimer'
import { render, screen, waitFor } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  restTimerApi: { get: vi.fn(), start: vi.fn(), extend: vi.fn(), stop: vi.fn(), subscribe: vi.fn() },
}))

function RestTimerHarness() {
  const restTimer = useRestTimer()
  const [restTimerSheetOpen, setRestTimerSheetOpen] = useState(false)
  return (
    <>
      <button
        type="button"
        onClick={() => {
          void restTimer.startRestTimer(90, 'ベンチプレス 2セット目')
          setRestTimerSheetOpen(true)
        }}
      >
        レスト
      </button>
      {restTimer.running !== null && (
        <>
          <RestTimerSheet
            open={restTimerSheetOpen}
            onClose={() => setRestTimerSheetOpen(false)}
            running={restTimer.running}
            notificationStatus={restTimer.notificationStatus}
            onExtend={restTimer.extendRestTimer}
            onStop={restTimer.stopRestTimer}
          />
          <RestTimerBadge
            remainingSeconds={restTimer.running.remainingSeconds}
            onOpen={() => setRestTimerSheetOpen(true)}
          />
        </>
      )}
      <Toaster />
    </>
  )
}

function buildRestTimerResponse(seconds: number, startedAtMs = Date.now()): RestTimerResponse {
  return {
    started_at: new Date(startedAtMs).toISOString(),
    ends_at: new Date(startedAtMs + seconds * 1000).toISOString(),
    total_seconds: seconds,
    next_set_label: 'ベンチプレス 2セット目',
  }
}

function buildPushSubscription(endpoint: string, applicationServerKey: number[]) {
  return {
    endpoint,
    options: { applicationServerKey: new Uint8Array(applicationServerKey).buffer },
    toJSON: () => ({ keys: { p256dh: 'p256dh', auth: 'auth' } }),
    unsubscribe: vi.fn().mockResolvedValue(true),
  }
}

/** 通知の許可と push の購読ができる端末にする。返す pushManager の振る舞いはテストごとに決める */
function stubPushSupportedDevice(permission: NotificationPermission, requestedPermission: NotificationPermission) {
  const pushManager = { getSubscription: vi.fn(), subscribe: vi.fn() }
  vi.stubGlobal('Notification', { permission, requestPermission: vi.fn().mockResolvedValue(requestedPermission) })
  vi.stubGlobal('PushManager', class {})
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: { ready: Promise.resolve({ pushManager }) },
  })
  return pushManager
}

const NOTIFICATION_DENIED_DEVICES = [
  { device: '通知を許可しない設定の端末', stubDevice: () => stubPushSupportedDevice('denied', 'denied') },
  { device: '通知の許可を求められて拒否した端末', stubDevice: () => stubPushSupportedDevice('default', 'denied') },
]

beforeEach(() => {
  vi.mocked(restTimerApi.get).mockResolvedValue(null)
})

afterEach(() => {
  vi.useRealTimers()
  vi.resetAllMocks()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  Reflect.deleteProperty(navigator, 'serviceWorker')
})

describe('RestTimerSheet', () => {
  it.each([
    { elapsedSeconds: 0, expected: '1:30' },
    { elapsedSeconds: 1, expected: '1:29' },
    { elapsedSeconds: 2, expected: '1:28' },
  ])(
    '通知に対応していない端末でも 90 秒のレストを開始すると、$elapsedSeconds 秒後の残り時間は $expected になる',
    async ({ elapsedSeconds, expected }) => {
      vi.stubGlobal('Notification', undefined)
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
      vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
      render(<RestTimerHarness />)

      fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
      await screen.findByRole('timer', { name: '残り時間' })
      act(() => vi.advanceTimersByTime(elapsedSeconds * 1000))

      expect(screen.getByRole('timer', { name: '残り時間' })).toHaveTextContent(expected)
    },
  )

  it.each(NOTIFICATION_DENIED_DEVICES)(
    '$device でも 90 秒のレストを開始すると、1 秒後の残り時間は 1:29 になる',
    async ({ stubDevice }) => {
      stubDevice()
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
      vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
      render(<RestTimerHarness />)

      fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
      await screen.findByRole('timer', { name: '残り時間' })
      act(() => vi.advanceTimersByTime(1000))

      expect(screen.getByRole('timer', { name: '残り時間' })).toHaveTextContent('1:29')
    },
  )

  it.each([
    { device: '通知に対応していない端末', stubDevice: () => vi.stubGlobal('Notification', undefined) },
    ...NOTIFICATION_DENIED_DEVICES,
  ])(
    '$device でレストを開始すると、通知がオフであることを表示する',
    async ({ stubDevice }) => {
      stubDevice()
      vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
      render(<RestTimerHarness />)

      fireEvent.click(screen.getByRole('button', { name: 'レスト' }))

      expect(await screen.findByText('通知はオフです。終了の通知は届きません')).toBeInTheDocument()
    },
  )

  it('通知の購読の登録に失敗すると、通知がオフであることを表示する', async () => {
    const pushManager = stubPushSupportedDevice('granted', 'granted')
    pushManager.getSubscription.mockResolvedValue(null)
    pushManager.subscribe.mockResolvedValue(buildPushSubscription('https://push.example.com/new', []))
    vi.mocked(restTimerApi.subscribe).mockRejectedValue(new Error('購読を登録できませんでした'))
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))

    expect(await screen.findByText('通知はオフです。終了の通知は届きません')).toBeInTheDocument()
  })

  it('以前と違う鍵で購読していた端末でレストを開始すると、購読を作り直して登録する', async () => {
    const pushManager = stubPushSupportedDevice('granted', 'granted')
    vi.stubEnv('VITE_VAPID_PUBLIC_KEY', 'BAUG')
    pushManager.getSubscription.mockResolvedValue(buildPushSubscription('https://push.example.com/old', [1, 2, 3]))
    pushManager.subscribe.mockResolvedValue(buildPushSubscription('https://push.example.com/new', [4, 5, 6]))
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))

    await waitFor(() =>
      expect(restTimerApi.subscribe).toHaveBeenCalledWith({
        endpoint: 'https://push.example.com/new',
        p256dh: 'p256dh',
        auth: 'auth',
      }),
    )
  })

  it('通知の予約に失敗した応答が返ると、開始できなかったことを表示する', async () => {
    vi.mocked(restTimerApi.start).mockRejectedValue(new Error('通知を予約できませんでした'))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))

    expect(await screen.findByText('レストタイマーを開始できませんでした')).toBeInTheDocument()
  })

  it('通知の予約に失敗した応答が返ると、残り時間を表示しない', async () => {
    vi.mocked(restTimerApi.start).mockRejectedValue(new Error('通知を予約できませんでした'))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    await screen.findByText('レストタイマーを開始できませんでした')

    expect(screen.queryByRole('button', { name: /^レスト / })).not.toBeInTheDocument()
  })

  it('端末の時計がサーバーより進んでいても、レストを開始した秒数から数える', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) =>
      buildRestTimerResponse(seconds, Date.now() - 10 * 60 * 1000),
    )
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))

    expect(await screen.findByRole('timer', { name: '残り時間' })).toHaveTextContent('1:30')
  })

  it('レストを続けて押すと、後に押した開始の応答を表示する', async () => {
    let resolveFirstStart: (response: RestTimerResponse) => void = () => {}
    vi.mocked(restTimerApi.start)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveFirstStart = resolve
        }),
      )
      .mockImplementationOnce(async ({ seconds }) => buildRestTimerResponse(seconds))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    await screen.findByRole('timer', { name: '残り時間' })
    await act(async () => resolveFirstStart(buildRestTimerResponse(60)))

    expect(screen.getByRole('timer', { name: '残り時間' })).toHaveTextContent('1:30')
  })

  it('延長の応答を待つ間は、+30秒を押せない', async () => {
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    vi.mocked(restTimerApi.extend).mockReturnValue(new Promise(() => {}))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    fireEvent.click(await screen.findByRole('button', { name: '+30秒' }))

    expect(screen.getByRole('button', { name: '+30秒' })).toBeDisabled()
  })

  it('停止に失敗すると、シートに残り時間を表示したままにする', async () => {
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    vi.mocked(restTimerApi.stop).mockRejectedValue(new Error('停止できませんでした'))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    fireEvent.click(await screen.findByRole('button', { name: '停止' }))
    await screen.findByText('レストタイマーを停止できませんでした')

    expect(screen.getByRole('timer', { name: '残り時間' })).toBeInTheDocument()
  })
})

describe('RestTimerBadge', () => {
  it('画面を開いたときに動いているレストを、続きの残り時間から表示する', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.mocked(restTimerApi.get).mockResolvedValue(buildRestTimerResponse(90, Date.now() - 30 * 1000))
    render(<RestTimerHarness />)

    expect(await screen.findByRole('button', { name: 'レスト 1:00' })).toBeInTheDocument()
  })

  it('レストの終了の1秒前は、残り時間を 0:01 と表示する', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    await screen.findByRole('button', { name: 'レスト 1:30' })
    act(() => vi.advanceTimersByTime(89 * 1000))

    expect(screen.getByRole('button', { name: /^レスト / })).toHaveTextContent('レスト 0:01')
  })

  it('レストの残りが0秒になると、残り時間の表示を消す', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    await screen.findByRole('button', { name: 'レスト 1:30' })
    act(() => vi.advanceTimersByTime(90 * 1000))

    expect(screen.queryByRole('button', { name: /^レスト / })).not.toBeInTheDocument()
  })
})
