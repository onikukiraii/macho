import { useId, useRef, useState, type ReactElement } from 'react'
import { Link } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { Button } from '@/components/dads/Button'
import { Textarea } from '@/components/dads/Textarea'
import { InputField } from '@/components/InputField'
import { RirSheet } from '@/components/RirSheet'
import { useLongPress } from '@/hooks/useLongPress'
import { formatSet } from '@/lib/exercises'
import {
  appendColumn,
  copyPreviousColumn,
  fillWeightForward,
  initializeColumns,
  toSetParams,
  type SetColumn,
} from '@/lib/setColumns'

type PerformedExercise = components['schemas']['PerformedExerciseResponse']

type PerformedExerciseCardProps = {
  trainingLogUid: string
  performedExercise: PerformedExercise
  onStartRest: (seconds: number, nextSetLabel: string) => void
}

function SetNumberButton({ setNumber, onLongPress }: { setNumber: number; onLongPress: () => void }): ReactElement {
  const longPressHandlers = useLongPress(onLongPress)
  return (
    <button type="button" {...longPressHandlers} className="h-8 select-none text-dns-14B-130">
      {setNumber}
    </button>
  )
}

function PlannedSummary({ performedExercise }: { performedExercise: PerformedExercise }): ReactElement | null {
  const { planned, target_weight: targetWeight, previous } = performedExercise
  if (planned === null && previous === null) return null
  return (
    <div className="flex flex-col gap-1 text-dns-14N-130 text-muted-foreground">
      {planned !== null && (
        <p>
          予定 {planned.sets}×{planned.reps}
          {planned.reps_max !== null && `〜${planned.reps_max}`}
          {planned.target_rpe !== null && ` RPE${planned.target_rpe}`}
          {planned.target_percent !== null && ` ${planned.target_percent}%`}
          {targetWeight !== null && ` / 目標 ${targetWeight} kg`}
        </p>
      )}
      {previous !== null && (
        <p>
          前回 {format(parseISO(previous.date), 'M/d')} {formatSet(previous.top_set)}
        </p>
      )}
    </div>
  )
}

export function PerformedExerciseCard({
  trainingLogUid,
  performedExercise,
  onStartRest,
}: PerformedExerciseCardProps): ReactElement {
  const headingId = useId()
  const [columns, setColumns] = useState(() => initializeColumns(performedExercise))
  const [saveFailed, setSaveFailed] = useState(false)
  const [rirColumnIndex, setRirColumnIndex] = useState<number | null>(null)
  const [memo, setMemo] = useState(performedExercise.memo)
  const savedSetsKey = useRef(JSON.stringify(toSetParams(initializeColumns(performedExercise))))
  const latestSaveRequest = useRef(0)

  // 全セットの置き換えなので、失敗したあとの送り直しは冪等になる
  async function saveSets(nextColumns: SetColumn[]): Promise<void> {
    const sets = toSetParams(nextColumns)
    const setsKey = JSON.stringify(sets)
    if (!saveFailed && setsKey === savedSetsKey.current) return
    latestSaveRequest.current += 1
    const request = latestSaveRequest.current
    try {
      await trainingLogsApi.replaceSets(performedExercise.uid, { sets })
      if (request !== latestSaveRequest.current) return
      savedSetsKey.current = setsKey
      setSaveFailed(false)
    } catch {
      if (request !== latestSaveRequest.current) return
      setSaveFailed(true)
      toast.error('セットを保存できませんでした')
    }
  }

  function commitColumns(nextColumns: SetColumn[]): void {
    setColumns(nextColumns)
    void saveSets(nextColumns)
  }

  function editColumn(index: number, patch: Partial<SetColumn>): SetColumn[] {
    return columns.map((column, position) => (position === index ? { ...column, ...patch } : column))
  }

  async function saveMemo(): Promise<void> {
    try {
      await trainingLogsApi.updateExercise(performedExercise.uid, { exercise_uid: performedExercise.exercise_uid, memo })
    } catch {
      toast.error('メモを保存できませんでした')
    }
  }

  const nextSetIndex = columns.findIndex((column) => column.weight === '' || column.reps === '')
  const weightPlaceholder = performedExercise.target_weight === null ? undefined : String(performedExercise.target_weight)
  const repsPlaceholder = performedExercise.planned === null ? undefined : String(performedExercise.planned.reps)

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3 rounded-8 bg-card p-3">
      <div className="flex items-start justify-between gap-4">
        <h2 id={headingId} className="text-std-18B-160">
          {performedExercise.exercise_name}
        </h2>
        <div className="flex shrink-0 items-center gap-2">
          {saveFailed && (
            <button
              type="button"
              onClick={() => void saveSets(columns)}
              className="rounded-4 bg-error-1 px-2 py-0.5 text-dns-14B-130 text-white"
            >
              未保存
            </button>
          )}
          <Link
            to={`/training-logs/${trainingLogUid}/exercise-picker?replace=${performedExercise.uid}`}
            className="text-dns-14N-130 text-primary underline"
          >
            差し替え
          </Link>
        </div>
      </div>
      <PlannedSummary performedExercise={performedExercise} />
      <p className="text-dns-14N-130 text-muted-foreground">
        セット番号を長押しすると、前のセットの重量・回数・RIR をコピーします
      </p>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {columns.map((column, index) => (
          <div key={index} className="flex w-16 shrink-0 flex-col items-stretch gap-1 text-center">
            {index === 0 ? (
              <span className="flex h-8 items-center justify-center text-dns-14B-130">1</span>
            ) : (
              <SetNumberButton setNumber={index + 1} onLongPress={() => commitColumns(copyPreviousColumn(columns, index))} />
            )}
            <input
              type="number"
              inputMode="decimal"
              step="any"
              min={0}
              max={500}
              aria-label={`セット${index + 1}の重量`}
              placeholder={weightPlaceholder}
              value={column.weight}
              onChange={(event) => setColumns(editColumn(index, { weight: event.target.value }))}
              onBlur={() => commitColumns(fillWeightForward(columns, index))}
              className="h-12 rounded-8 border border-solid-gray-600 bg-white text-center text-oln-16N-100 text-solid-gray-800 placeholder:text-solid-gray-420"
            />
            <input
              type="number"
              inputMode="numeric"
              step={1}
              min={0}
              max={100}
              aria-label={`セット${index + 1}の回数`}
              placeholder={repsPlaceholder}
              value={column.reps}
              onChange={(event) => setColumns(editColumn(index, { reps: event.target.value }))}
              onBlur={() => commitColumns(columns)}
              className="h-12 rounded-8 border border-solid-gray-600 bg-white text-center text-oln-16N-100 text-solid-gray-800 placeholder:text-solid-gray-420"
            />
            <button
              type="button"
              aria-label={`セット${index + 1}の RIR`}
              onClick={() => setRirColumnIndex(index)}
              className="h-12 rounded-8 border border-solid-gray-600 text-oln-16N-100"
            >
              {column.rir ?? '-'}
            </button>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Button size="md" variant="outline" onClick={() => setColumns(appendColumn(columns))}>
          セットを追加
        </Button>
        <Button
          size="md"
          variant="solid-fill"
          onClick={() =>
            onStartRest(
              performedExercise.default_rest_seconds,
              nextSetIndex === -1
                ? performedExercise.exercise_name
                : `${performedExercise.exercise_name} セット${nextSetIndex + 1}`,
            )
          }
        >
          レスト {Math.floor(performedExercise.default_rest_seconds / 60)}:
          {String(performedExercise.default_rest_seconds % 60).padStart(2, '0')}
        </Button>
      </div>
      <InputField label="メモ">
        <Textarea rows={2} maxLength={1000} value={memo} onChange={(event) => setMemo(event.target.value)} onBlur={() => void saveMemo()} />
      </InputField>
      <RirSheet
        open={rirColumnIndex !== null}
        onClose={() => setRirColumnIndex(null)}
        onDecide={(rir) => rirColumnIndex !== null && commitColumns(editColumn(rirColumnIndex, { rir }))}
      />
    </section>
  )
}
