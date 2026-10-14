import type { ReactElement } from 'react'
import { Link } from 'react-router-dom'
import { exercisesApi } from '@/api/fetcher'
import { BODY_PART_LABEL, EXERCISE_KIND_LABEL, type Exercise } from '@/api/constants'
import { Button } from '@/components/dads/Button'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { groupExercisesByBodyPart } from '@/lib/exercises'

const LOAD_FAILURE_MESSAGE = '種目の一覧を取得できませんでした'

function ExerciseRow({ exercise }: { exercise: Exercise }): ReactElement {
  return (
    <li>
      <Link
        to={`/exercises/${exercise.uid}`}
        className="flex min-h-14 items-center justify-between gap-4 border-b border-border px-4 py-2"
      >
        <span className="flex flex-col">
          <span className="text-std-16B-170">{exercise.name}</span>
          <span className="text-dns-14N-130 text-muted-foreground">{EXERCISE_KIND_LABEL[exercise.kind]}</span>
        </span>
        <span className="text-dns-14N-130 text-muted-foreground">
          {exercise.kind === 'derived'
            ? `${exercise.parent_name} × ${exercise.coefficient}`
            : `トレーニングマックス ${exercise.current_training_max === null ? '未設定' : `${exercise.current_training_max} kg`}`}
        </span>
      </Link>
    </li>
  )
}

export function ExercisesPage(): ReactElement {
  const [exercises] = useLoadable(() => exercisesApi.list(), [], LOAD_FAILURE_MESSAGE)

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="flex items-center justify-between px-4">
        <h1 className="text-std-24B-150">種目</h1>
        <Button asChild size="sm" variant="solid-fill">
          <Link to="/exercises/new">種目を追加</Link>
        </Button>
      </div>
      {exercises.status === 'loading' && <Skeleton className="mx-4 h-40" />}
      {exercises.status === 'failed' && <p className="px-4 text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>}
      {exercises.status === 'loaded' &&
        groupExercisesByBodyPart(exercises.value).map((group) => (
          <section key={group.bodyPart} className="flex flex-col">
            <h2 className="px-4 py-2 text-dns-14B-130 text-muted-foreground">{BODY_PART_LABEL[group.bodyPart]}</h2>
            <ul>
              {group.exercises.map((exercise) => (
                <ExerciseRow key={exercise.uid} exercise={exercise} />
              ))}
            </ul>
          </section>
        ))}
    </div>
  )
}
