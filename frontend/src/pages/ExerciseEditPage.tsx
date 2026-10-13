import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { exercisesApi } from '@/api/fetcher'
import { Button } from '@/components/dads/Button'
import { Input } from '@/components/dads/Input'
import { Select } from '@/components/dads/Select'
import { Skeleton } from '@/components/ui/skeleton'

type Exercise = Awaited<ReturnType<typeof exercisesApi.list>>[number]

type ExerciseFormProps = {
  exercises: Exercise[]
  editing: Exercise | null
  initialName: string
  returnTo: string | null
}

function ExerciseForm({ exercises, editing, initialName, returnTo }: ExerciseFormProps) {
  const navigate = useNavigate()
  const [name, setName] = useState(editing?.name ?? initialName)
  const [parentUid, setParentUid] = useState(editing?.parent_uid ?? '')
  const [coefficient, setCoefficient] = useState(editing?.coefficient?.toString() ?? '1')
  const [e1rmDivisor, setE1rmDivisor] = useState(editing?.e1rm_divisor.toString() ?? '33.3')
  const [incrementKg, setIncrementKg] = useState(editing?.increment_kg.toString() ?? '2.5')
  const [defaultRestSeconds, setDefaultRestSeconds] = useState(editing?.default_rest_seconds.toString() ?? '90')
  const [saving, setSaving] = useState(false)

  const parentCandidates = exercises.filter(
    (exercise) => exercise.kind === 'training_max' && exercise.uid !== editing?.uid,
  )

  async function saveExercise(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    const params = {
      name,
      parent_uid: parentUid === '' ? null : parentUid,
      coefficient: parentUid === '' ? null : Number(coefficient),
      e1rm_divisor: parentUid === '' ? Number(e1rmDivisor) : null,
      increment_kg: Number(incrementKg),
      default_rest_seconds: Number(defaultRestSeconds),
    }
    try {
      const saved = editing === null ? await exercisesApi.create(params) : await exercisesApi.update(editing.uid, params)
      if (returnTo === null) {
        navigate(`/exercises/${saved.uid}`)
      } else if (editing === null) {
        const destination = new URL(returnTo, window.location.origin)
        destination.searchParams.set('createdExerciseUid', saved.uid)
        navigate(destination.pathname + destination.search)
      } else {
        navigate(returnTo)
      }
    } catch {
      toast.error('種目を保存できませんでした')
      setSaving(false)
    }
  }

  return (
    <form onSubmit={saveExercise} className="flex flex-col gap-4 p-4">
      <h1 className="text-std-24B-150">{editing === null ? '種目を作成' : '種目を編集'}</h1>
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">名前</span>
        <Input required maxLength={64} value={name} onChange={(event) => setName(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">派生元の種目</span>
        <Select value={parentUid} onChange={(event) => setParentUid(event.target.value)}>
          <option value="">なし</option>
          {parentCandidates.map((exercise) => (
            <option key={exercise.uid} value={exercise.uid}>
              {exercise.name}
            </option>
          ))}
        </Select>
      </label>
      {parentUid === '' ? (
        <label className="flex flex-col gap-1">
          <span className="text-std-16B-170">1RM の推定式の分母</span>
          <Input type="number" inputMode="decimal" step="any" min={0} max={100} required value={e1rmDivisor} onChange={(event) => setE1rmDivisor(event.target.value)} />
        </label>
      ) : (
        <label className="flex flex-col gap-1">
          <span className="text-std-16B-170">換算係数</span>
          <Input type="number" inputMode="decimal" step="any" min={0} max={2} required value={coefficient} onChange={(event) => setCoefficient(event.target.value)} />
        </label>
      )}
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">上げる幅 (kg)</span>
        <Input type="number" inputMode="decimal" step="any" min={0} max={20} required value={incrementKg} onChange={(event) => setIncrementKg(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">レスト秒数</span>
        <Input type="number" inputMode="numeric" step={1} min={1} max={900} required value={defaultRestSeconds} onChange={(event) => setDefaultRestSeconds(event.target.value)} />
      </label>
      <Button type="submit" size="lg" variant="solid-fill" aria-disabled={saving} className="w-full">
        {saving ? '保存中' : '保存する'}
      </Button>
    </form>
  )
}

export function ExerciseEditPage() {
  const { uid } = useParams<{ uid: string }>()
  const [searchParams] = useSearchParams()
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

  if (exercises === null) return <Skeleton className="m-4 h-60" />
  if (exercises === 'failed') return <p className="p-4 text-muted-foreground">種目の一覧を取得できませんでした</p>

  const editing = exercises.find((exercise) => exercise.uid === uid) ?? null
  if (uid !== undefined && editing === null) return <p className="p-4 text-muted-foreground">種目が見つかりません</p>

  const returnTo = searchParams.get('returnTo')
  return (
    <ExerciseForm
      exercises={exercises}
      editing={editing}
      initialName={searchParams.get('name') ?? ''}
      returnTo={returnTo !== null && /^\/(?![/\\])/.test(returnTo) ? returnTo : null}
    />
  )
}
