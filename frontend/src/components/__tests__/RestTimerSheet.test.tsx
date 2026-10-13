import { useState } from 'react'
import { act, fireEvent } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { restTimerApi } from '@/api/fetcher'
import { RestTimerSheet } from '@/components/RestTimerSheet'
import { Toaster } from '@/components/ui/sonner'
import { useRestTimer } from '@/hooks/useRestTimer'
import { render, screen } from '@/test/utils'

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
      <RestTimerSheet open={restTimerSheetOpen} onClose={() => setRestTimerSheetOpen(false)} restTimer={restTimer} />
      <Toaster />
    </>
  )
}

function buildRestTimerResponse(seconds: number) {
  const startedAt = Date.now()
  return {
    started_at: new Date(startedAt).toISOString(),
    ends_at: new Date(startedAt + seconds * 1000).toISOString(),
    total_seconds: seconds,
    next_set_label: 'ベンチプレス 2セット目',
  }
}

// jsdom は dialog の showModal と close を実装していない
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true
  }
  HTMLDialogElement.prototype.close = function () {
    this.open = false
  }
})

beforeEach(() => {
  vi.mocked(restTimerApi.get).mockResolvedValue(null)
})

afterEach(() => {
  vi.useRealTimers()
  vi.resetAllMocks()
})

describe('RestTimerSheet', () => {
  it('通知に対応していない端末でもレストを開始すると、残り時間が1秒ごとに減る', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    await screen.findByRole('timer', { name: '残り時間' })
    act(() => vi.advanceTimersByTime(1000))

    expect(screen.getByRole('timer', { name: '残り時間' })).toHaveTextContent('1:29')
  })

  it('通知に対応していない端末でレストを開始すると、通知がオフであることを表示する', async () => {
    vi.mocked(restTimerApi.start).mockImplementation(async ({ seconds }) => buildRestTimerResponse(seconds))
    render(<RestTimerHarness />)

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))

    expect(await screen.findByText('通知はオフです。終了の通知は届きません')).toBeInTheDocument()
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
    // 画面を開いたときのタイマーの取得を終えてから押す。取得の応答が開始の結果を上書きしないようにする
    await act(async () => {})

    fireEvent.click(screen.getByRole('button', { name: 'レスト' }))
    await screen.findByText('レストタイマーを開始できませんでした')

    expect(screen.queryByRole('timer', { name: '残り時間' })).not.toBeInTheDocument()
  })
})
