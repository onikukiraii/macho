import { fireEvent, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '@/api/schema'
import { restTimerApi, trainingLogsApi } from '@/api/fetcher'
import { TrainingLogPage } from '@/pages/TrainingLogPage'
import { render, screen, waitFor } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  trainingLogsApi: { get: vi.fn(), update: vi.fn(), delete: vi.fn(), replaceSets: vi.fn(), updateExercise: vi.fn() },
  restTimerApi: { get: vi.fn(), start: vi.fn(), extend: vi.fn(), stop: vi.fn(), subscribe: vi.fn() },
}))

type TrainingLogDetail = components['schemas']['TrainingLogDetailResponse']

function buildTrainingLog(overrides: Partial<TrainingLogDetail>): TrainingLogDetail {
  return {
    uid: 'log-1',
    date: '2026-10-14',
    day_label: null,
    week_label: null,
    guide_date: null,
    memo: '',
    exercises: [],
    ...overrides,
  }
}

function renderTrainingLogPage() {
  return render(
    <Routes>
      <Route path="/" element={<p>ホームの画面</p>} />
      <Route path="/training-logs/:uid" element={<TrainingLogPage />} />
    </Routes>,
  )
}

async function openDeleteConfirmation(): Promise<HTMLElement> {
  fireEvent.click(await screen.findByRole('button', { name: '記録を削除' }))
  return screen.getByRole('dialog', { name: 'トレーニング記録を削除' })
}

beforeEach(() => {
  vi.mocked(restTimerApi.get).mockResolvedValue(null)
  vi.mocked(trainingLogsApi.get).mockResolvedValue(buildTrainingLog({}))
  window.history.pushState({}, '', '/training-logs/log-1')
})

afterEach(() => {
  vi.resetAllMocks()
})

describe('TrainingLogPage', () => {
  it('削除を押すと、確認のダイアログを開く', async () => {
    renderTrainingLogPage()

    const confirmation = await openDeleteConfirmation()

    expect(confirmation).toHaveAttribute('open')
  })

  it('確認でキャンセルを押すと、ダイアログを閉じる', async () => {
    renderTrainingLogPage()

    const confirmation = await openDeleteConfirmation()
    fireEvent.click(within(confirmation).getByRole('button', { name: 'キャンセル' }))

    await waitFor(() => expect(confirmation).not.toHaveAttribute('open'))
  })

  it('確認でキャンセルを押すと、記録を削除せず記録の画面に残る', async () => {
    renderTrainingLogPage()

    const confirmation = await openDeleteConfirmation()
    fireEvent.click(within(confirmation).getByRole('button', { name: 'キャンセル' }))
    await waitFor(() => expect(confirmation).not.toHaveAttribute('open'))

    expect({
      deleted: vi.mocked(trainingLogsApi.delete).mock.calls.length > 0,
      pathname: window.location.pathname,
    }).toEqual({ deleted: false, pathname: '/training-logs/log-1' })
  })

  it('確認で削除するを押すと、記録を削除してホームへ移る', async () => {
    vi.mocked(trainingLogsApi.delete).mockResolvedValue(undefined)
    renderTrainingLogPage()

    const confirmation = await openDeleteConfirmation()
    fireEvent.click(within(confirmation).getByRole('button', { name: '削除する' }))
    await screen.findByText('ホームの画面')

    expect(trainingLogsApi.delete).toHaveBeenCalledWith('log-1')
  })

  it('記録を削除してホームへ移ると、履歴に記録の画面を残さない', async () => {
    vi.mocked(trainingLogsApi.delete).mockResolvedValue(undefined)
    renderTrainingLogPage()
    const historyLength = window.history.length

    const confirmation = await openDeleteConfirmation()
    fireEvent.click(within(confirmation).getByRole('button', { name: '削除する' }))
    await screen.findByText('ホームの画面')

    expect(window.history.length).toBe(historyLength)
  })

  it('未保存の種目があるときにホームへ戻るを押すと、移動する前に確認を開く', async () => {
    vi.mocked(trainingLogsApi.get).mockResolvedValue(
      buildTrainingLog({
        exercises: [
          {
            uid: 'performed-1',
            exercise_uid: 'exercise-1',
            exercise_name: 'ベンチプレス',
            planned: null,
            target_weight: null,
            previous: null,
            default_rest_seconds: 180,
            memo: '',
            sets: [],
          },
        ],
      }),
    )
    vi.mocked(trainingLogsApi.replaceSets).mockRejectedValue(new Error('サーバーとの通信に失敗しました'))
    renderTrainingLogPage()

    fireEvent.change(await screen.findByRole('spinbutton', { name: 'セット1の重量' }), { target: { value: '100' } })
    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の回数' }), { target: { value: '5' } })
    fireEvent.blur(screen.getByRole('spinbutton', { name: 'セット1の回数' }))
    await screen.findByRole('button', { name: '未保存' })
    fireEvent.click(screen.getByRole('link', { name: 'ホームへ戻る' }))

    expect(screen.getByRole('dialog', { name: '未保存のセットがあります' })).toHaveAttribute('open')
  })
})
