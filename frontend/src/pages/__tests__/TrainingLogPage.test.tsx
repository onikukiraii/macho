import { fireEvent, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { restTimerApi, trainingLogsApi } from '@/api/fetcher'
import { TrainingLogPage } from '@/pages/TrainingLogPage'
import { render, screen } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  trainingLogsApi: { get: vi.fn(), update: vi.fn(), delete: vi.fn(), replaceSets: vi.fn(), updateExercise: vi.fn() },
  restTimerApi: { get: vi.fn(), start: vi.fn(), extend: vi.fn(), stop: vi.fn(), subscribe: vi.fn() },
}))

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
  vi.mocked(trainingLogsApi.get).mockResolvedValue({
    uid: 'log-1',
    date: '2026-10-14',
    day_label: null,
    week_label: null,
    guide_date: null,
    memo: '',
    exercises: [],
  })
  window.history.pushState({}, '', '/training-logs/log-1')
})

afterEach(() => {
  vi.resetAllMocks()
})

describe('TrainingLogPage', () => {
  it('削除を押すと確認が表示され、キャンセルを押すと記録を削除しない', async () => {
    render(
      <Routes>
        <Route path="/training-logs/:uid" element={<TrainingLogPage />} />
      </Routes>,
    )

    fireEvent.click(await screen.findByRole('button', { name: '記録を削除' }))
    const confirmation = screen.getByRole('dialog', { name: 'トレーニング記録を削除' })
    fireEvent.click(within(confirmation).getByRole('button', { name: 'キャンセル' }))

    expect(trainingLogsApi.delete).not.toHaveBeenCalled()
  })
})
