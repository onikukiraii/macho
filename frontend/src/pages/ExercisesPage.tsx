import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { exercisesApi } from '@/api/fetcher'
import { EXERCISE_KIND_LABEL, type ExerciseKind } from '@/api/constants'
import { Button } from '@/components/dads/Button'
import { Skeleton } from '@/components/ui/skeleton'

type Exercise = Awaited<ReturnType<typeof exercisesApi.list>>[number]

const KIND_ORDER: ExerciseKind[] = ['training_max', 'derived', 'double_progression']

function ExerciseRow({ exercise }: { exercise: Exercise }) {
  return (
    <li>
      <Link
        to={`/exercises/${exercise.uid}`}
        className="flex min-h-14 items-center justify-between gap-4 border-b border-border px-4 py-2"
      >
        <span className="text-std-16B-170">{exercise.name}</span>
        <span className="text-dns-14N-130 text-muted-foreground">
          {exercise.kind === 'training_max' && `TM ${exercise.current_training_max} kg`}
          {exercise.kind === 'derived' && `${exercise.parent_name} × ${exercise.coefficient}`}
        </span>
      </Link>
    </li>
  )
}

export function ExercisesPage() {
  const [exercises, setExercises] = useState<Exercise[] | 'failed' | null>(null)

  useEffect(() => {
    let cancelled = false
    exercisesApi
      .list()
      .then((list) => !cancelled && setExercises(list))
      .catch(() => {
        if (cancelled) return
        toast.error('種目の一覧を取得できませんでした')
        setExercises('failed')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="flex items-center justify-between px-4">
        <h1 className="text-std-24B-150">種目</h1>
        <Button asChild size="sm" variant="solid-fill">
          <Link to="/exercises/new">種目を追加</Link>
        </Button>
      </div>
      {exercises === null && <Skeleton className="mx-4 h-40" />}
      {exercises === 'failed' && <p className="px-4 text-muted-foreground">種目の一覧を取得できませんでした</p>}
      {Array.isArray(exercises) &&
        KIND_ORDER.map((kind) => (
          <section key={kind} className="flex flex-col">
            <h2 className="px-4 py-2 text-dns-14B-130 text-muted-foreground">{EXERCISE_KIND_LABEL[kind]}</h2>
            <ul>
              {exercises
                .filter((exercise) => exercise.kind === kind)
                .map((exercise) => (
                  <ExerciseRow key={exercise.uid} exercise={exercise} />
                ))}
            </ul>
          </section>
        ))}
    </div>
  )
}
