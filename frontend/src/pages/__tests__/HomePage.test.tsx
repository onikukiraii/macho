import { act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { trainingLogsApi } from '@/api/fetcher'
import { HomePage } from '@/pages/HomePage'
import { render, screen } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  trainingLogsApi: { list: vi.fn(), latest: vi.fn(), dayOptions: vi.fn(), create: vi.fn() },
}))

beforeEach(() => {
  vi.mocked(trainingLogsApi.list).mockResolvedValue([])
  vi.mocked(trainingLogsApi.latest).mockResolvedValue(null)
  vi.mocked(trainingLogsApi.dayOptions).mockResolvedValue({ options: [] })
  window.history.pushState({}, '', '/')
})

afterEach(() => {
  vi.useRealTimers()
  vi.resetAllMocks()
})

describe('HomePage', () => {
  it('日をまたいで開いたままの画面に戻ると、新しい今日を選ぶ', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 9, 14, 23, 59))
    render(<HomePage />)
    await screen.findByRole('heading', { name: '10月14日の記録' })

    vi.setSystemTime(new Date(2026, 9, 15, 0, 1))
    act(() => {
      window.dispatchEvent(new Event('focus'))
    })

    expect(await screen.findByRole('heading', { name: '10月15日の記録' })).toBeInTheDocument()
  })
})
