import { fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '@/api/schema'
import { exercisesApi, restTimerApi, trainingLogsApi } from '@/api/fetcher'
import { ExerciseEditPage } from '@/pages/ExerciseEditPage'
import { ExercisePickerPage } from '@/pages/ExercisePickerPage'
import { TrainingLogPage } from '@/pages/TrainingLogPage'
import { render, screen, waitFor } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  exercisesApi: { list: vi.fn(), create: vi.fn() },
  trainingLogsApi: {
    get: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    addExercise: vi.fn(),
    replaceExercise: vi.fn(),
    updateExerciseMemo: vi.fn(),
    replaceSets: vi.fn(),
  },
  restTimerApi: { get: vi.fn(), start: vi.fn(), extend: vi.fn(), stop: vi.fn(), subscribe: vi.fn() },
}))

type Exercise = components['schemas']['ExerciseResponse']

function buildExercise(overrides: Partial<Exercise>): Exercise {
  return {
    uid: 'exercise-1',
    name: 'スクワット',
    kind: 'training_max',
    parent_uid: null,
    parent_name: null,
    coefficient: null,
    e1rm_divisor: 33.3,
    increment_kg: 2.5,
    default_rest_seconds: 180,
    current_training_max: null,
    ...overrides,
  }
}

const TRAINING_LOG_WITH_CREATED_EXERCISE: components['schemas']['TrainingLogDetailResponse'] = {
  uid: 'log-1',
  date: '2026-10-14',
  day_label: null,
  week_label: null,
  guide_date: null,
  memo: '',
  exercises: [
    {
      uid: 'performed-1',
      exercise_uid: 'exercise-created',
      exercise_name: 'ベンチ',
      planned: null,
      target_weight: null,
      previous: null,
      default_rest_seconds: 90,
      memo: '',
      sets: [],
    },
  ],
}

beforeEach(() => {
  vi.mocked(restTimerApi.get).mockResolvedValue(null)
  vi.mocked(exercisesApi.list).mockResolvedValue([buildExercise({})])
  vi.mocked(exercisesApi.create).mockResolvedValue(buildExercise({ uid: 'exercise-created', name: 'ベンチ' }))
  vi.mocked(trainingLogsApi.addExercise).mockResolvedValue(TRAINING_LOG_WITH_CREATED_EXERCISE)
  vi.mocked(trainingLogsApi.get).mockResolvedValue(TRAINING_LOG_WITH_CREATED_EXERCISE)
  window.history.pushState({}, '', '/training-logs/log-1/exercise-picker')
})

afterEach(() => {
  vi.resetAllMocks()
})

describe('ExercisePickerPage', () => {
  it('見つからない名前から種目を作成すると、その種目をトレーニング記録に追加して記録の画面へ戻る', async () => {
    render(
      <Routes>
        <Route path="/training-logs/:uid" element={<TrainingLogPage />} />
        <Route path="/training-logs/:uid/exercise-picker" element={<ExercisePickerPage />} />
        <Route path="/exercises/new" element={<ExerciseEditPage />} />
      </Routes>,
    )

    fireEvent.change(await screen.findByRole('searchbox', { name: '種目を検索' }), { target: { value: 'ベンチ' } })
    fireEvent.click(screen.getByRole('link', { name: '新しい種目として作成' }))
    expect(await screen.findByRole('textbox', { name: '名前' })).toHaveValue('ベンチ')
    fireEvent.click(screen.getByRole('button', { name: '保存する' }))

    expect(await screen.findByRole('region', { name: 'ベンチ' })).toBeInTheDocument()
    await waitFor(() =>
      expect(trainingLogsApi.addExercise).toHaveBeenCalledWith('log-1', { exercise_uid: 'exercise-created' }),
    )
  })

  it('種目を差し替えると、記録を取り直さずに差し替え先の種目で更新して記録の画面へ戻る', async () => {
    window.history.pushState({}, '', '/training-logs/log-1/exercise-picker?replace=performed-1')
    vi.mocked(trainingLogsApi.replaceExercise).mockResolvedValue(TRAINING_LOG_WITH_CREATED_EXERCISE)
    render(
      <Routes>
        <Route path="/training-logs/:uid" element={<p>記録の画面</p>} />
        <Route path="/training-logs/:uid/exercise-picker" element={<ExercisePickerPage />} />
      </Routes>,
    )

    fireEvent.click(await screen.findByRole('button', { name: 'スクワット' }))

    expect(await screen.findByText('記録の画面')).toBeInTheDocument()
    expect(trainingLogsApi.replaceExercise).toHaveBeenCalledWith('performed-1', 'exercise-1')
    expect(trainingLogsApi.get).not.toHaveBeenCalled()
  })
})
