import { useCallback, useEffect, useId, useRef, useState, type ReactElement } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { BODY_PART_LABEL } from '@/api/constants'
import { exercisesApi, trainingLogsApi } from '@/api/fetcher'
import { Input } from '@/components/dads/Input'
import { InputField } from '@/components/InputField'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { groupExercisesByBodyPart } from '@/lib/exercises'

const LOAD_FAILURE_MESSAGE = '種目の一覧を取得できませんでした'

function ExercisePicker({ trainingLogUid }: { trainingLogUid: string }): ReactElement {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const replacingUid = searchParams.get('replace')
  const createdExerciseUid = searchParams.get('createdExerciseUid')
  const [exercises] = useLoadable(() => exercisesApi.list(), [], LOAD_FAILURE_MESSAGE)
  const [query, setQuery] = useState('')
  const headingId = useId()
  const pickedCreatedExerciseUid = useRef<string | null>(null)
  const picking = useRef(false)

  const pickExercise = useCallback(
    async (exerciseUid: string): Promise<void> => {
      if (picking.current) return
      picking.current = true
      try {
        if (replacingUid === null) {
          await trainingLogsApi.addExercise(trainingLogUid, { exercise_uid: exerciseUid })
        } else {
          await trainingLogsApi.replaceExercise(replacingUid, exerciseUid)
        }
        navigate(`/training-logs/${trainingLogUid}`, { replace: true })
      } catch {
        picking.current = false
        toast.error(replacingUid === null ? '種目を追加できませんでした' : '種目を差し替えできませんでした')
      }
    },
    [navigate, replacingUid, trainingLogUid],
  )

  // 種目の編集画面で作成して戻ってきたら、その種目を記録に追加する。StrictMode で effect が再実行されても2回追加しないよう、追加した uid を ref に持つ
  useEffect(() => {
    if (createdExerciseUid === null || pickedCreatedExerciseUid.current === createdExerciseUid) return
    pickedCreatedExerciseUid.current = createdExerciseUid
    void pickExercise(createdExerciseUid)
  }, [createdExerciseUid, pickExercise])

  const trimmedQuery = query.trim()
  const matchedExercises =
    exercises.status === 'loaded' ? exercises.value.filter((exercise) => exercise.name.includes(trimmedQuery)) : []
  const exactMatchExists = matchedExercises.some((exercise) => exercise.name === trimmedQuery)
  const createExerciseHref = `/exercises/new?${new URLSearchParams({
    name: trimmedQuery,
    returnTo: location.pathname + location.search,
  })}`

  return (
    <div className="flex flex-col gap-4 p-4">
      <Link to={`/training-logs/${trainingLogUid}`} className="text-dns-14N-130 text-primary underline">
        記録へ戻る
      </Link>
      <h1 className="text-std-24B-150">{replacingUid === null ? '種目を追加' : '種目を差し替え'}</h1>
      <InputField label="種目を検索">
        <Input type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
      </InputField>
      {exercises.status === 'loading' && <Skeleton className="h-40" />}
      {exercises.status === 'failed' && <p className="text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>}
      {exercises.status === 'loaded' && trimmedQuery !== '' && !exactMatchExists && (
        <Link to={createExerciseHref} className="flex min-h-12 items-center rounded-8 bg-card px-4 text-std-16B-170 text-primary">
          新しい種目として作成
        </Link>
      )}
      {groupExercisesByBodyPart(matchedExercises).map((group) => (
        <section key={group.bodyPart} aria-labelledby={`${headingId}-${group.bodyPart}`} className="flex flex-col">
          <h2 id={`${headingId}-${group.bodyPart}`} className="text-dns-14B-130 text-muted-foreground">
            {BODY_PART_LABEL[group.bodyPart]}
          </h2>
          <ul className="flex flex-col divide-y divide-border">
            {group.exercises.map((exercise) => (
              <li key={exercise.uid}>
                <button
                  type="button"
                  onClick={() => void pickExercise(exercise.uid)}
                  className="flex min-h-12 w-full items-center text-left text-std-16N-170"
                >
                  {exercise.name}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

export function ExercisePickerPage(): ReactElement {
  const { uid } = useParams<{ uid: string }>()
  if (uid === undefined) return <p className="p-4 text-muted-foreground">トレーニング記録が見つかりません</p>
  return <ExercisePicker trainingLogUid={uid} />
}
