import { useState, type ReactElement } from 'react'
import { Link, useParams } from 'react-router-dom'
import { exercisesApi, trainingLogsApi } from '@/api/fetcher'
import { EXERCISE_KIND_LABEL, type ExerciseDetail } from '@/api/constants'
import { Button } from '@/components/Button'
import { Skeleton } from '@/components/ui/skeleton'
import { TrainingMaxChangeSheet } from '@/components/TrainingMaxChangeSheet'
import { useLoadable, type Loadable } from '@/hooks/useLoadable'
import { formatDateString, formatLocalDate } from '@/lib/dates'
import { formatSet } from '@/lib/exercises'

const DETAIL_FAILURE_MESSAGE = '種目を取得できませんでした'
const HISTORY_FAILURE_MESSAGE = '種目ごとの記録を取得できませんでした'

type TrainingMaxSectionProps = {
  detail: Loadable<ExerciseDetail>
  onChanged: (detail: ExerciseDetail) => void
}

function TrainingMaxSection({ detail, onChanged }: TrainingMaxSectionProps): ReactElement | null {
  const [changing, setChanging] = useState(false)

  if (detail.status === 'failed') return null
  if (detail.status === 'loading') return <Skeleton className="h-40" />

  const { exercise, training_max_history: trainingMaxHistory } = detail.value
  if (exercise.kind === 'derived') return null

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-std-20B-150">トレーニングマックス</h2>
        <Button size="sm" variant="outline" onClick={() => setChanging(true)}>
          変更
        </Button>
      </div>
      <p className="text-std-32B-150">
        {exercise.current_training_max === null ? '未設定' : `${exercise.current_training_max} kg`}
      </p>
      <ul className="flex flex-col divide-y divide-border">
        {trainingMaxHistory.map((trainingMax) => (
          <li key={trainingMax.effective_at} className="flex flex-col gap-1 py-2">
            <span className="flex items-baseline gap-2 text-std-16B-170">
              {trainingMax.value} kg
              <span className="text-dns-14N-130 text-muted-foreground">{formatLocalDate(trainingMax.effective_at)}</span>
            </span>
            <span className="text-dns-14N-130 text-muted-foreground">{trainingMax.reason}</span>
          </li>
        ))}
      </ul>
      <TrainingMaxChangeSheet
        open={changing}
        onClose={() => setChanging(false)}
        exercise={exercise}
        onChanged={onChanged}
      />
    </section>
  )
}

function ExerciseHistorySection({ uid }: { uid: string }): ReactElement {
  const [history] = useLoadable(() => trainingLogsApi.byExercise(uid), [uid], HISTORY_FAILURE_MESSAGE)

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-std-20B-150">記録</h2>
      {history.status === 'loading' && <Skeleton className="h-24" />}
      {history.status === 'failed' && <p className="text-muted-foreground">{HISTORY_FAILURE_MESSAGE}</p>}
      {history.status === 'loaded' && history.value.length === 0 && <p className="text-muted-foreground">記録はありません</p>}
      {history.status === 'loaded' &&
        history.value.map((entry) => (
          <article key={entry.training_log_uid} className="flex flex-col gap-1 rounded-8 bg-card p-3">
            <Link to={`/training-logs/${entry.training_log_uid}`} className="flex items-baseline gap-2 text-std-16B-170">
              {formatDateString(entry.date)}
              {entry.day_label !== null && <span className="text-dns-14N-130 text-muted-foreground">{entry.day_label}</span>}
            </Link>
            <ul className="text-dns-14N-130">
              {entry.sets.map((set) => (
                <li key={set.order}>{formatSet(set)}</li>
              ))}
            </ul>
          </article>
        ))}
    </section>
  )
}

function ExerciseDetailView({ uid }: { uid: string }): ReactElement {
  const [detail, setDetail] = useLoadable(() => exercisesApi.get(uid), [uid], DETAIL_FAILURE_MESSAGE)

  return (
    <div className="flex flex-col gap-6 p-4">
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          {detail.status === 'loaded' ? (
            <>
              <h1 className="text-std-24B-150">{detail.value.exercise.name}</h1>
              <p className="text-dns-14N-130 text-muted-foreground">{EXERCISE_KIND_LABEL[detail.value.exercise.kind]}</p>
            </>
          ) : detail.status === 'loading' ? (
            <>
              <Skeleton className="h-9 w-40" />
              <Skeleton className="h-5 w-32" />
            </>
          ) : null}
        </div>
        <Button asChild size="sm" variant="outline">
          <Link to={`/exercises/${uid}/edit`}>編集</Link>
        </Button>
      </header>
      {detail.status === 'failed' && <p className="text-muted-foreground">{DETAIL_FAILURE_MESSAGE}</p>}
      <TrainingMaxSection detail={detail} onChanged={setDetail} />
      <ExerciseHistorySection uid={uid} />
    </div>
  )
}

export function ExerciseDetailPage(): ReactElement {
  const { uid } = useParams<{ uid: string }>()
  if (uid === undefined) return <p className="p-4 text-muted-foreground">種目が見つかりません</p>
  return <ExerciseDetailView uid={uid} />
}
