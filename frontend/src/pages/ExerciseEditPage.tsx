import { useState, type FormEvent, type ReactElement } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import type { Exercise } from '@/api/constants'
import { exercisesApi } from '@/api/fetcher'
import { Button } from '@/components/dads/Button'
import { Input } from '@/components/dads/Input'
import { Select } from '@/components/dads/Select'
import { InputField } from '@/components/InputField'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { resolveReturnTo } from '@/lib/returnTo'

const LOAD_FAILURE_MESSAGE = '種目の一覧を取得できませんでした'

type ExerciseFormProps = {
  exercises: Exercise[]
  editing: Exercise | null
  initialName: string
  returnTo: string | null
}

function ExerciseForm({ exercises, editing, initialName, returnTo }: ExerciseFormProps): ReactElement {
  const navigate = useNavigate()
  const [name, setName] = useState(editing?.name ?? initialName)
  const [parentUid, setParentUid] = useState(editing?.parent_uid ?? '')
  const [coefficient, setCoefficient] = useState(editing?.coefficient?.toString() ?? '1')
  const [e1rmDivisor, setE1rmDivisor] = useState(editing?.e1rm_divisor.toString() ?? '33.3')
  const [incrementKg, setIncrementKg] = useState(editing?.increment_kg.toString() ?? '2.5')
  const [defaultRestSeconds, setDefaultRestSeconds] = useState(editing?.default_rest_seconds.toString() ?? '90')
  const [saving, setSaving] = useState(false)

  const parentCandidates = exercises.filter((exercise) => exercise.kind !== 'derived' && exercise.uid !== editing?.uid)
  const parent = parentCandidates.find((exercise) => exercise.uid === parentUid)

  async function saveExercise(event: FormEvent): Promise<void> {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    const params = {
      name,
      parent_uid: parent === undefined ? null : parent.uid,
      coefficient: parent === undefined ? null : Number(coefficient),
      e1rm_divisor: parent === undefined ? Number(e1rmDivisor) : null,
      increment_kg: Number(incrementKg),
      default_rest_seconds: Number(defaultRestSeconds),
    }
    try {
      const saved = editing === null ? await exercisesApi.create(params) : await exercisesApi.update(editing.uid, params)
      const destination =
        returnTo === null
          ? null
          : resolveReturnTo(returnTo, window.location.origin, editing === null ? { createdExerciseUid: saved.uid } : {})
      if (destination === null) navigate(`/exercises/${saved.uid}`)
      else navigate(destination, { replace: true })
    } catch (error) {
      if (!(error instanceof Error)) throw error
      toast.error(`種目を保存できませんでした。${error.message}`)
      setSaving(false)
    }
  }

  return (
    <form onSubmit={saveExercise} className="flex flex-col gap-4">
      <InputField label="名前">
        <Input required maxLength={64} value={name} onChange={(event) => setName(event.target.value)} />
      </InputField>
      <InputField label="派生元の種目">
        <Select value={parentUid} onChange={(event) => setParentUid(event.target.value)}>
          <option value="">なし</option>
          {parentCandidates.map((exercise) => (
            <option key={exercise.uid} value={exercise.uid}>
              {exercise.name}
            </option>
          ))}
        </Select>
      </InputField>
      <InputField label="1RM の推定式の分母">
        <Input
          type="number"
          inputMode="decimal"
          step="any"
          min={0.01}
          max={100}
          required
          aria-disabled={parent !== undefined}
          value={parent === undefined ? e1rmDivisor : parent.e1rm_divisor}
          onChange={(event) => setE1rmDivisor(event.target.value)}
        />
      </InputField>
      {parent !== undefined && (
        <InputField label="換算係数">
          <Input
            type="number"
            inputMode="decimal"
            step="any"
            min={0.01}
            max={2}
            required
            value={coefficient}
            onChange={(event) => setCoefficient(event.target.value)}
          />
        </InputField>
      )}
      <InputField label="上げる幅 (kg)">
        <Input
          type="number"
          inputMode="decimal"
          step="any"
          min={0.01}
          max={20}
          required
          value={incrementKg}
          onChange={(event) => setIncrementKg(event.target.value)}
        />
      </InputField>
      <InputField label="レスト秒数">
        <Input
          type="number"
          inputMode="numeric"
          step={1}
          min={1}
          max={900}
          required
          value={defaultRestSeconds}
          onChange={(event) => setDefaultRestSeconds(event.target.value)}
        />
      </InputField>
      <Button type="submit" size="lg" variant="solid-fill" aria-disabled={saving} className="w-full">
        {saving ? '保存中' : '保存する'}
      </Button>
    </form>
  )
}

export function ExerciseEditPage(): ReactElement {
  const { uid } = useParams<{ uid: string }>()
  const [searchParams] = useSearchParams()
  const [exercises] = useLoadable(() => exercisesApi.list(), [], LOAD_FAILURE_MESSAGE)

  const editing = exercises.status === 'loaded' ? (exercises.value.find((exercise) => exercise.uid === uid) ?? null) : null

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-std-24B-150">{uid === undefined ? '種目を作成' : '種目を編集'}</h1>
      {exercises.status === 'loading' && <Skeleton className="h-60" />}
      {exercises.status === 'failed' && <p className="text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>}
      {exercises.status === 'loaded' && uid !== undefined && editing === null && (
        <p className="text-muted-foreground">種目が見つかりません</p>
      )}
      {exercises.status === 'loaded' && (uid === undefined || editing !== null) && (
        <ExerciseForm
          exercises={exercises.value}
          editing={editing}
          initialName={searchParams.get('name') ?? ''}
          returnTo={searchParams.get('returnTo')}
        />
      )}
    </div>
  )
}
