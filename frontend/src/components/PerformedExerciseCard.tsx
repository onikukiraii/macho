import { Fragment, useId, useRef, useState, type MouseEvent, type ReactElement } from 'react'
import { Link } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import type { components } from '@/api/schema'
import { Button } from '@/components/dads/Button'
import { ErrorText } from '@/components/dads/ErrorText'
import { PerformedExerciseMemoField } from '@/components/PerformedExerciseMemoField'
import { RirSheet } from '@/components/RirSheet'
import { useLongPress } from '@/hooks/useLongPress'
import { useSetsAutosave } from '@/hooks/useSetsAutosave'
import { formatPlanned, formatSet } from '@/lib/exercises'
import { formatRestTime } from '@/lib/restTimer'
import {
  MAX_COLUMN_COUNT,
  appendColumn,
  copyPreviousColumn,
  fillWeightForward,
  isValidReps,
  isValidWeight,
  type SetColumn,
} from '@/lib/setColumns'

type PerformedExercise = components['schemas']['PerformedExerciseResponse']

type PerformedExerciseCardProps = {
  trainingLogUid: string
  performedExercise: PerformedExercise
  onStartRest: (seconds: number, nextSetLabel: string) => void
  onUnsavedChange: (unsaved: boolean) => void
  /** 記録の画面から離れるリンクを押したとき。未保存の確認のため遷移を止めることがある */
  onNavigate: (event: MouseEvent<HTMLAnchorElement>, to: string) => void
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
      {planned !== null && <p>予定 {formatPlanned(planned, targetWeight)}</p>}
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
  onUnsavedChange,
  onNavigate,
}: PerformedExerciseCardProps): ReactElement {
  const headingId = useId()
  const columnErrorId = useId()
  const addColumnReasonId = useId()
  const { columns, editColumns, commitColumns, saveFailed, retrySave } = useSetsAutosave(performedExercise, onUnsavedChange)
  const [rirColumnIndex, setRirColumnIndex] = useState<number | null>(null)
  // 重量を変更せずに欄を離れたときは、後ろの列へ重量をコピーしない。後ろの列で消した重量が戻らないようにするため
  const editedWeightIndex = useRef<number | null>(null)

  function updateColumn(index: number, patch: Partial<SetColumn>): SetColumn[] {
    return columns.map((column, position) => (position === index ? { ...column, ...patch } : column))
  }

  function commitWeight(index: number): void {
    commitColumns(editedWeightIndex.current === index ? fillWeightForward(columns, index) : columns)
    editedWeightIndex.current = null
  }

  const nextSetIndex = columns.findIndex((column) => column.weight === '' || column.reps === '')
  const weightPlaceholder = performedExercise.target_weight === null ? undefined : String(performedExercise.target_weight)
  const repsPlaceholder = performedExercise.planned === null ? undefined : String(performedExercise.planned.reps)
  const columnLimitReached = columns.length >= MAX_COLUMN_COUNT
  const replaceExerciseHref = `/training-logs/${trainingLogUid}/exercise-picker?replace=${performedExercise.uid}`

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
              onClick={retrySave}
              className="rounded-4 bg-error-1 px-2 py-0.5 text-dns-14B-130 text-white"
            >
              未保存
            </button>
          )}
          <Link
            to={replaceExerciseHref}
            onClick={(event) => onNavigate(event, replaceExerciseHref)}
            className="text-dns-14N-130 text-primary underline"
          >
            差し替え
          </Link>
        </div>
      </div>
      {saveFailed && <ErrorText>セットを保存できませんでした</ErrorText>}
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
              aria-invalid={!isValidWeight(column.weight)}
              aria-describedby={isValidWeight(column.weight) ? undefined : `${columnErrorId}-weight-${index}`}
              placeholder={weightPlaceholder}
              value={column.weight}
              onChange={(event) => {
                editedWeightIndex.current = index
                editColumns(updateColumn(index, { weight: event.target.value }))
              }}
              onBlur={() => commitWeight(index)}
              className="h-12 rounded-8 border border-solid-gray-600 bg-white text-center text-oln-16N-100 text-solid-gray-800 dark:bg-solid-gray-900 dark:text-solid-gray-50 placeholder:text-solid-gray-420 aria-invalid:border-error-1"
            />
            <input
              type="number"
              inputMode="numeric"
              step={1}
              min={0}
              max={100}
              aria-label={`セット${index + 1}の回数`}
              aria-invalid={!isValidReps(column.reps)}
              aria-describedby={isValidReps(column.reps) ? undefined : `${columnErrorId}-reps-${index}`}
              placeholder={repsPlaceholder}
              value={column.reps}
              onChange={(event) => editColumns(updateColumn(index, { reps: event.target.value }))}
              onBlur={() => commitColumns(columns)}
              className="h-12 rounded-8 border border-solid-gray-600 bg-white text-center text-oln-16N-100 text-solid-gray-800 dark:bg-solid-gray-900 dark:text-solid-gray-50 placeholder:text-solid-gray-420 aria-invalid:border-error-1"
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
      {columns.map((column, index) => (
        <Fragment key={index}>
          {!isValidWeight(column.weight) && (
            <ErrorText id={`${columnErrorId}-weight-${index}`}>セット{index + 1}の重量は 0〜500 kg で入力してください</ErrorText>
          )}
          {!isValidReps(column.reps) && (
            <ErrorText id={`${columnErrorId}-reps-${index}`}>
              セット{index + 1}の回数は 0〜100 の整数で入力してください
            </ErrorText>
          )}
        </Fragment>
      ))}
      <div className="flex gap-2">
        <Button
          size="md"
          variant="outline"
          className="dark:bg-transparent dark:text-key-300"
          aria-disabled={columnLimitReached}
          aria-describedby={columnLimitReached ? addColumnReasonId : undefined}
          onClick={() => !columnLimitReached && editColumns(appendColumn(columns))}
        >
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
          レスト {formatRestTime(performedExercise.default_rest_seconds)}
        </Button>
      </div>
      {columnLimitReached && (
        <p id={addColumnReasonId} className="text-dns-14N-130 text-muted-foreground">
          セットは{MAX_COLUMN_COUNT}まで追加できます
        </p>
      )}
      <PerformedExerciseMemoField performedExercise={performedExercise} />
      <RirSheet
        open={rirColumnIndex !== null}
        onClose={() => setRirColumnIndex(null)}
        onDecide={(rir) => rirColumnIndex !== null && commitColumns(updateColumn(rirColumnIndex, { rir }))}
      />
    </section>
  )
}
