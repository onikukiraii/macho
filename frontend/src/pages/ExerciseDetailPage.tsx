import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { exercisesApi, trainingLogsApi } from '@/api/fetcher'
import { EXERCISE_KIND_LABEL } from '@/api/constants'
import { Button } from '@/components/dads/Button'
import { Skeleton } from '@/components/ui/skeleton'
import { TrainingMaxChangeSheet } from '@/components/TrainingMaxChangeSheet'

type ExerciseDetail = Awaited<ReturnType<typeof exercisesApi.get>>
type History = Awaited<ReturnType<typeof trainingLogsApi.byExercise>>

function formatSet(set: History[number]['sets'][number]): string {
  return `${set.weight} kg × ${set.reps}${set.rir === null ? '' : ` RIR ${set.rir}`}`
}

export function ExerciseDetailPage() {
  const { uid } = useParams<{ uid: string }>()
  const [detail, setDetail] = useState<ExerciseDetail | 'failed' | null>(null)
  const [history, setHistory] = useState<History | 'failed' | null>(null)
  const [changing, setChanging] = useState(false)

  useEffect(() => {
    if (uid === undefined) return
    let cancelled = false
    exercisesApi
      .get(uid)
      .then((loaded) => !cancelled && setDetail(loaded))
      .catch(() => {
        if (cancelled) return
        toast.error('種目を取得できませんでした')
        setDetail('failed')
      })
    trainingLogsApi
      .byExercise(uid)
      .then((loaded) => !cancelled && setHistory(loaded))
      .catch(() => {
        if (cancelled) return
        toast.error('種目ごとの記録を取得できませんでした')
        setHistory('failed')
      })
    return () => {
      cancelled = true
    }
  }, [uid])

  if (detail === null) return <Skeleton className="m-4 h-40" />
  if (detail === 'failed') return <p className="p-4 text-muted-foreground">種目を取得できませんでした</p>

  const { exercise, training_max_history: trainingMaxHistory } = detail

  return (
    <div className="flex flex-col gap-6 p-4">
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-std-24B-150">{exercise.name}</h1>
          <p className="text-dns-14N-130 text-muted-foreground">{EXERCISE_KIND_LABEL[exercise.kind]}</p>
        </div>
        <Button asChild size="sm" variant="outline">
          <Link to={`/exercises/${exercise.uid}/edit`}>編集</Link>
        </Button>
      </header>

      {exercise.parent_uid === null && (
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
                <span className="text-std-16B-170">
                  {trainingMax.value} kg
                  <span className="ml-2 text-dns-14N-130 text-muted-foreground">
                    {new Date(trainingMax.effective_at).toLocaleDateString('ja-JP')}
                  </span>
                </span>
                <span className="text-dns-14N-130 text-muted-foreground">{trainingMax.reason}</span>
              </li>
            ))}
          </ul>
          <TrainingMaxChangeSheet
            open={changing}
            onClose={() => setChanging(false)}
            exercise={exercise}
            onChanged={setDetail}
          />
        </section>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-std-20B-150">記録</h2>
        {history === null && <Skeleton className="h-24" />}
        {history === 'failed' && <p className="text-muted-foreground">種目ごとの記録を取得できませんでした</p>}
        {Array.isArray(history) && history.length === 0 && <p className="text-muted-foreground">記録はありません</p>}
        {Array.isArray(history) &&
          history.map((entry) => (
            <article key={entry.training_log_uid} className="flex flex-col gap-1 rounded-8 bg-card p-3">
              <Link to={`/training-logs/${entry.training_log_uid}`} className="text-std-16B-170">
                {entry.date}
                {entry.day_label !== null && <span className="ml-2 text-dns-14N-130 text-muted-foreground">{entry.day_label}</span>}
              </Link>
              <ul className="text-dns-14N-130">
                {entry.sets.map((set) => (
                  <li key={set.order}>{formatSet(set)}</li>
                ))}
              </ul>
            </article>
          ))}
      </section>
    </div>
  )
}
