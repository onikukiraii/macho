import { fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { components } from '@/api/schema'
import { exercisesApi } from '@/api/fetcher'
import { ExerciseEditPage } from '@/pages/ExerciseEditPage'
import { render, screen, waitFor } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  exercisesApi: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
}))

const LAT_PULLDOWN: components['schemas']['ExerciseResponse'] = {
  uid: 'lat',
  name: 'ラットプルダウン',
  body_part: 'back',
  kind: 'double_progression',
  parent_uid: null,
  parent_name: null,
  coefficient: null,
  e1rm_divisor: 33.3,
  increment_kg: 2.5,
  default_rest_seconds: 90,
  current_training_max: null,
}

afterEach(() => {
  vi.resetAllMocks()
})

describe('ExerciseEditPage', () => {
  it('種目を作成すると、選択した部位を送る', async () => {
    vi.mocked(exercisesApi.list).mockResolvedValue([])
    vi.mocked(exercisesApi.create).mockResolvedValue(LAT_PULLDOWN)
    window.history.pushState({}, '', '/exercises/new')
    render(
      <Routes>
        <Route path="/exercises/new" element={<ExerciseEditPage />} />
        <Route path="/exercises/:uid" element={<p>詳細</p>} />
      </Routes>,
    )

    fireEvent.change(await screen.findByRole('textbox', { name: '名前' }), { target: { value: 'ラットプルダウン' } })
    fireEvent.change(screen.getByRole('combobox', { name: '部位' }), { target: { value: 'back' } })
    fireEvent.click(screen.getByRole('button', { name: '保存する' }))

    await waitFor(() =>
      expect(exercisesApi.create).toHaveBeenCalledWith(expect.objectContaining({ body_part: 'back' })),
    )
  })

  it('種目を編集するときは、保存されている部位を選択した状態で開く', async () => {
    vi.mocked(exercisesApi.list).mockResolvedValue([LAT_PULLDOWN])
    window.history.pushState({}, '', '/exercises/lat/edit')
    render(
      <Routes>
        <Route path="/exercises/:uid/edit" element={<ExerciseEditPage />} />
      </Routes>,
    )

    expect(await screen.findByRole('combobox', { name: '部位' })).toHaveValue('back')
  })
})
