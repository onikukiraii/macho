import { fireEvent, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '@/api/schema'
import { analyticsApi, exercisesApi } from '@/api/fetcher'
import { AnalyticsPage } from '@/pages/AnalyticsPage'
import { render, screen } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  analyticsApi: { overview: vi.fn(), exercise: vi.fn() },
  exercisesApi: { list: vi.fn() },
}))

const OVERVIEW: components['schemas']['OverviewResponse'] = {
  summary: { total_volume: 1800, change_rate: 0.2, training_days: 2, set_count: 4, volume_per_training_day: 900 },
  weekly_volumes: [
    { start: '2026-09-28', volumes: [{ body_part: 'chest', volume: 800 }] },
    { start: '2026-10-05', volumes: [{ body_part: 'back', volume: 500 }] },
  ],
  monthly_volumes: [{ start: '2026-10-01', volumes: [{ body_part: 'chest', volume: 1300 }] }],
  body_part_shares: [{ body_part: 'chest', volume: 1300, share: 1 }],
  annual: { year: 2026, this_year: [{ month: 1, cumulative_volume: 1300 }], last_year: [], change_rate: null, last_year_total_volume: 0 },
  big3: { lifts: [{ exercise_name: 'ベンチプレス', e1rm: 92 }], total: 92, goal: 400 },
}

beforeEach(() => {
  vi.mocked(analyticsApi.overview).mockResolvedValue(OVERVIEW)
  vi.mocked(exercisesApi.list).mockResolvedValue([
    {
      uid: 'bench',
      name: 'ベンチプレス',
      body_part: 'chest',
      kind: 'training_max',
      parent_uid: null,
      parent_name: null,
      coefficient: null,
      e1rm_divisor: 40,
      increment_kg: 2.5,
      default_rest_seconds: 180,
      current_training_max: 90.5,
    },
  ])
  vi.mocked(analyticsApi.exercise).mockResolvedValue({
    exercise_name: 'ベンチプレス',
    max_weight: 82.5,
    max_e1rm: 92.8,
    total_volume: 1207.5,
    e1rm_points: [{ date: '2026-10-01', e1rm: 92 }],
    training_max_points: [{ effective_on: '2026-10-01', value: 88 }],
    weekly_volumes: [{ start: '2026-09-28', volume: 960 }],
    monthly_volumes: [{ start: '2026-10-01', volume: 1207.5 }],
  })
})

afterEach(() => {
  vi.resetAllMocks()
})

function renderAnalyticsPage(): void {
  window.history.pushState({}, '', '/analytics')
  render(
    <Routes>
      <Route path="/analytics" element={<AnalyticsPage />} />
    </Routes>,
  )
}

describe('AnalyticsPage', () => {
  it('種目タブを押すと、種目の選択欄と種目の指標が表示される', async () => {
    renderAnalyticsPage()

    fireEvent.click(screen.getByRole('link', { name: '種目' }))

    expect(await screen.findByRole('combobox', { name: '種目' })).toBeInTheDocument()
    expect(await screen.findByText('推定1RM の最大')).toBeInTheDocument()
  })

  it('種目タブを押すと、URL の tab が exercise になる', () => {
    renderAnalyticsPage()

    fireEvent.click(screen.getByRole('link', { name: '種目' }))

    expect(new URLSearchParams(window.location.search).get('tab')).toBe('exercise')
  })

  it('総ボリュームで週を押すと、週ごとの棒に切り替わる', async () => {
    renderAnalyticsPage()

    fireEvent.click(await screen.findByRole('button', { name: '週' }))

    expect(within(screen.getByRole('img', { name: '週ごとの総ボリューム' })).getByText('9/28')).toBeInTheDocument()
  })
})
