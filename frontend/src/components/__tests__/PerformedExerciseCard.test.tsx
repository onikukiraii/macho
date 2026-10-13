import { fireEvent, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { PerformedExerciseCard } from '@/components/PerformedExerciseCard'
import { Toaster } from '@/components/ui/sonner'
import { render, screen, waitFor } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  trainingLogsApi: { replaceSets: vi.fn(), updateExercise: vi.fn() },
}))

type PerformedExercise = components['schemas']['PerformedExerciseResponse']

function buildPerformedExercise(overrides: Partial<PerformedExercise>): PerformedExercise {
  return {
    uid: 'performed-1',
    exercise_uid: 'exercise-1',
    exercise_name: 'ベンチプレス',
    planned: null,
    target_weight: null,
    previous: null,
    default_rest_seconds: 180,
    memo: '',
    sets: [],
    ...overrides,
  }
}

afterEach(() => {
  vi.resetAllMocks()
})

describe('PerformedExerciseCard', () => {
  it('予定種目の空の列には目標重量と予定の回数をプレースホルダに出し、予定外の種目には5つの空の列を並べる', () => {
    render(
      <>
        <PerformedExerciseCard
          trainingLogUid="log-1"
          performedExercise={buildPerformedExercise({
            exercise_name: 'ベンチプレス',
            planned: { sets: 4, reps: 5, reps_max: null, target_rpe: 7.5, target_percent: null },
            target_weight: 75,
          })}
          onStartRest={vi.fn()}
        />
        <PerformedExerciseCard
          trainingLogUid="log-1"
          performedExercise={buildPerformedExercise({ uid: 'performed-2', exercise_name: 'ディップス' })}
          onStartRest={vi.fn()}
        />
      </>,
    )
    const benchPress = within(screen.getByRole('region', { name: 'ベンチプレス' }))
    const dips = within(screen.getByRole('region', { name: 'ディップス' }))

    expect(
      benchPress.getAllByRole('spinbutton', { name: /の重量$/ }).map((weightInput, index) => [
        weightInput.getAttribute('placeholder'),
        benchPress.getByRole('spinbutton', { name: `セット${index + 1}の回数` }).getAttribute('placeholder'),
      ]),
    ).toEqual([
      ['75', '5'],
      ['75', '5'],
      ['75', '5'],
      ['75', '5'],
    ])
    expect(dips.getAllByRole('spinbutton', { name: /の重量$/ })).toHaveLength(5)
  })

  it('セットの保存が失敗すると入力を残して未保存を表示し、列の変更か未保存の押下で全セットを送り直す', async () => {
    vi.mocked(trainingLogsApi.replaceSets).mockRejectedValue(new Error('サーバーとの通信に失敗しました'))
    render(
      <>
        <PerformedExerciseCard
          trainingLogUid="log-1"
          performedExercise={buildPerformedExercise({})}
          onStartRest={vi.fn()}
        />
        <Toaster />
      </>,
    )

    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の重量' }), { target: { value: '100' } })
    fireEvent.blur(screen.getByRole('spinbutton', { name: 'セット1の重量' }))
    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の回数' }), { target: { value: '5' } })
    fireEvent.blur(screen.getByRole('spinbutton', { name: 'セット1の回数' }))

    expect(await screen.findByText('セットを保存できませんでした')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '未保存' })).toBeInTheDocument()
    expect(screen.getByRole('spinbutton', { name: 'セット1の回数' })).toHaveValue(5)

    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット2の回数' }), { target: { value: '4' } })
    fireEvent.blur(screen.getByRole('spinbutton', { name: 'セット2の回数' }))
    await waitFor(() =>
      expect(trainingLogsApi.replaceSets).toHaveBeenLastCalledWith('performed-1', {
        sets: [
          { order: 1, weight: 100, reps: 5, rir: null },
          { order: 2, weight: 100, reps: 4, rir: null },
        ],
      }),
    )

    vi.mocked(trainingLogsApi.replaceSets).mockClear()
    vi.mocked(trainingLogsApi.replaceSets).mockResolvedValue(
      buildPerformedExercise({
        sets: [
          { order: 1, weight: 100, reps: 5, rir: null },
          { order: 2, weight: 100, reps: 4, rir: null },
        ],
      }),
    )
    fireEvent.click(await screen.findByRole('button', { name: '未保存' }))

    await waitFor(() => expect(screen.queryByRole('button', { name: '未保存' })).not.toBeInTheDocument())
    expect(trainingLogsApi.replaceSets).toHaveBeenCalledWith('performed-1', {
      sets: [
        { order: 1, weight: 100, reps: 5, rir: null },
        { order: 2, weight: 100, reps: 4, rir: null },
      ],
    })
  })
})
