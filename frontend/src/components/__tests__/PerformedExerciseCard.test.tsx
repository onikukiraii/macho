import { act, fireEvent, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { PerformedExerciseCard } from '@/components/PerformedExerciseCard'
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

function deferPromise<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve: (value: T) => void = () => {}
  const promise = new Promise<T>((settle) => {
    resolve = settle
  })
  return { promise, resolve }
}

function renderCard(performedExercise: PerformedExercise) {
  return render(
    <PerformedExerciseCard
      trainingLogUid="log-1"
      performedExercise={performedExercise}
      onStartRest={vi.fn()}
      onUnsavedChange={vi.fn()}
      onNavigate={vi.fn()}
    />,
  )
}

function enterValue(name: string, value: string): void {
  fireEvent.change(screen.getByRole('spinbutton', { name }), { target: { value } })
  fireEvent.blur(screen.getByRole('spinbutton', { name }))
}

afterEach(() => {
  vi.useRealTimers()
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
          onUnsavedChange={vi.fn()}
          onNavigate={vi.fn()}
        />
        <PerformedExerciseCard
          trainingLogUid="log-1"
          performedExercise={buildPerformedExercise({ uid: 'performed-2', exercise_name: 'ディップス' })}
          onStartRest={vi.fn()}
          onUnsavedChange={vi.fn()}
          onNavigate={vi.fn()}
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
    renderCard(buildPerformedExercise({}))
    const benchPress = within(screen.getByRole('region', { name: 'ベンチプレス' }))

    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の重量' }), { target: { value: '100' } })
    fireEvent.blur(screen.getByRole('spinbutton', { name: 'セット1の重量' }))
    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の回数' }), { target: { value: '5' } })
    fireEvent.blur(screen.getByRole('spinbutton', { name: 'セット1の回数' }))

    expect(await benchPress.findByText('セットを保存できませんでした')).toBeInTheDocument()
    expect(benchPress.getByRole('button', { name: '未保存' })).toBeInTheDocument()
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

  it('セットの送信中に列を変えると、送信が終わってから最新の列を1回だけ送る', async () => {
    const firstSave = deferPromise<PerformedExercise>()
    vi.mocked(trainingLogsApi.replaceSets)
      .mockReturnValueOnce(firstSave.promise)
      .mockResolvedValue(buildPerformedExercise({}))
    renderCard(buildPerformedExercise({}))

    enterValue('セット1の重量', '100')
    enterValue('セット1の回数', '5')
    enterValue('セット1の回数', '6')
    enterValue('セット1の回数', '7')
    await act(async () => firstSave.resolve(buildPerformedExercise({})))

    await waitFor(() =>
      expect(vi.mocked(trainingLogsApi.replaceSets).mock.calls.map(([, body]) => body.sets)).toEqual([
        [{ order: 1, weight: 100, reps: 5, rir: null }],
        [{ order: 1, weight: 100, reps: 7, rir: null }],
      ]),
    )
  })

  it('セットの送信中に値を元に戻すと、戻した値を送り直す', async () => {
    const firstSave = deferPromise<PerformedExercise>()
    vi.mocked(trainingLogsApi.replaceSets)
      .mockReturnValueOnce(firstSave.promise)
      .mockResolvedValue(buildPerformedExercise({}))
    renderCard(buildPerformedExercise({ sets: [{ order: 1, weight: 100, reps: 5, rir: null }] }))

    enterValue('セット1の回数', '6')
    enterValue('セット1の回数', '5')
    await act(async () => firstSave.resolve(buildPerformedExercise({})))

    await waitFor(() =>
      expect(vi.mocked(trainingLogsApi.replaceSets).mock.calls.map(([, body]) => body.sets)).toEqual([
        [{ order: 1, weight: 100, reps: 6, rir: null }],
        [{ order: 1, weight: 100, reps: 5, rir: null }],
      ]),
    )
  })

  it.each([
    { name: 'セット1の重量', value: '501', description: 'セット1の重量は 0〜500 kg で入力してください' },
    { name: 'セット1の回数', value: '2.5', description: 'セット1の回数は 0〜100 の整数で入力してください' },
  ])('$name に $value を入力すると、入力欄にエラーを表示する', ({ name, value, description }) => {
    renderCard(buildPerformedExercise({}))

    fireEvent.change(screen.getByRole('spinbutton', { name }), { target: { value } })

    expect(screen.getByRole('spinbutton', { name })).toHaveAccessibleDescription(description)
  })

  it('範囲外の値の列がある間は、セットを送らない', () => {
    renderCard(buildPerformedExercise({ sets: [{ order: 1, weight: 100, reps: 5, rir: null }] }))

    enterValue('セット1の重量', '501')
    enterValue('セット2の重量', '100')
    enterValue('セット2の回数', '5')

    expect(trainingLogsApi.replaceSets).not.toHaveBeenCalled()
  })

  it('セットが50列あると、セットを追加できない理由を表示する', () => {
    renderCard(buildPerformedExercise({ sets: [{ order: 50, weight: 100, reps: 5, rir: null }] }))

    expect(screen.getByRole('button', { name: 'セットを追加' })).toHaveAccessibleDescription('セットは50まで追加できます')
  })

  it('セット番号を長押しすると、押している間に入力した値も含めて前の列をコピーする', () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    vi.mocked(trainingLogsApi.replaceSets).mockResolvedValue(buildPerformedExercise({}))
    renderCard(buildPerformedExercise({}))

    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の重量' }), { target: { value: '100' } })
    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の回数' }), { target: { value: '5' } })
    fireEvent.pointerDown(screen.getByRole('button', { name: '2' }))
    fireEvent.change(screen.getByRole('spinbutton', { name: 'セット1の回数' }), { target: { value: '6' } })
    act(() => vi.advanceTimersByTime(500))

    expect(screen.getByRole('spinbutton', { name: 'セット2の回数' })).toHaveValue(6)
  })

  it('重量を変えずに欄を離れても、消した列に重量を入れ直さない', () => {
    vi.mocked(trainingLogsApi.replaceSets).mockResolvedValue(buildPerformedExercise({}))
    renderCard(buildPerformedExercise({}))

    enterValue('セット1の重量', '100')
    enterValue('セット2の重量', '')
    fireEvent.focus(screen.getByRole('spinbutton', { name: 'セット1の重量' }))
    fireEvent.blur(screen.getByRole('spinbutton', { name: 'セット1の重量' }))

    expect(screen.getByRole('spinbutton', { name: 'セット2の重量' })).toHaveValue(null)
  })
})
