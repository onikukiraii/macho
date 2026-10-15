import { fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { programImportsApi } from '@/api/fetcher'
import { Toaster } from '@/components/ui/sonner'
import { ProgramPreviewPage } from '@/pages/ProgramPreviewPage'
import { render, screen } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  programImportsApi: { preview: vi.fn(), create: vi.fn() },
}))

beforeEach(() => {
  vi.mocked(programImportsApi.preview).mockResolvedValue({
    status: 'valid',
    name: 'ベンチ スモロフ Jr',
    start_date: '2026-10-19',
    tm_auto_update: false,
    design_note: '',
    new_exercises: [],
    weeks: [
      {
        week: 1,
        label: '導入',
        days: [
          {
            day: 1,
            weekday: 'mon',
            exercises: [
              {
                exercise_name: 'ベンチプレス',
                is_new_exercise: false,
                sets: 6,
                reps: 6,
                reps_max: null,
                target_rpe: null,
                target_percent: 70,
                target_weight: 62.5,
              },
            ],
          },
        ],
      },
    ],
  })
  vi.mocked(programImportsApi.create).mockResolvedValue({ uid: 'program', name: 'ベンチ スモロフ Jr' })
})

afterEach(() => {
  vi.resetAllMocks()
})

async function addProgram(): Promise<void> {
  window.history.pushState({ usr: { jsonText: '{}' }, key: 'preview', idx: 1 }, '', '/program/preview')
  render(
    <>
      <Routes>
        <Route path="/program/preview" element={<ProgramPreviewPage />} />
        <Route path="/program" element={<p>プログラム画面</p>} />
      </Routes>
      <Toaster />
    </>,
  )
  fireEvent.click(await screen.findByRole('button', { name: 'このプログラムを追加' }))
}

describe('ProgramPreviewPage', () => {
  it('このプログラムを追加を押すと、プログラム画面へ移る', async () => {
    await addProgram()

    expect(await screen.findByText('プログラム画面')).toBeInTheDocument()
  })

  it('このプログラムを追加を押すと、追加したことをトーストで表示する', async () => {
    await addProgram()

    expect(await screen.findByText('プログラムを追加しました')).toBeInTheDocument()
  })
})
