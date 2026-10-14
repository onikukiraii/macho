import { useState, type FormEvent, type ReactElement } from 'react'
import { toast } from 'sonner'
import type { Exercise, ExerciseDetail } from '@/api/constants'
import { exercisesApi } from '@/api/fetcher'
import { BottomSheet } from '@/components/BottomSheet'
import { Button } from '@/components/dads/Button'
import { Input } from '@/components/dads/Input'
import { InputField } from '@/components/InputField'

type TrainingMaxChangeSheetProps = {
  open: boolean
  onClose: () => void
  exercise: Exercise
  onChanged: (detail: ExerciseDetail) => void
}

function TrainingMaxChangeForm({ exercise, onClose, onChanged }: Omit<TrainingMaxChangeSheetProps, 'open'>): ReactElement {
  const [value, setValue] = useState(exercise.current_training_max?.toString() ?? '')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)

  async function submitTrainingMax(event: FormEvent): Promise<void> {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      onChanged(await exercisesApi.createTrainingMax(exercise.uid, { value: Number(value), reason }))
      onClose()
    } catch (error) {
      if (!(error instanceof Error)) throw error
      toast.error(`トレーニングマックスを変更できませんでした。${error.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submitTrainingMax} className="flex flex-col gap-4">
      <InputField label="トレーニングマックス (kg)">
        <Input
          type="number"
          inputMode="decimal"
          step="any"
          min={0.01}
          max={500}
          required
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
      </InputField>
      <InputField label="理由">
        <Input type="text" maxLength={255} required value={reason} onChange={(event) => setReason(event.target.value)} />
      </InputField>
      <Button type="submit" size="lg" variant="solid-fill" aria-disabled={saving} className="w-full">
        {saving ? '保存中' : '変更する'}
      </Button>
    </form>
  )
}

export function TrainingMaxChangeSheet({ open, onClose, exercise, onChanged }: TrainingMaxChangeSheetProps): ReactElement {
  return (
    <BottomSheet open={open} onClose={onClose} title="トレーニングマックスを変更">
      <TrainingMaxChangeForm exercise={exercise} onClose={onClose} onChanged={onChanged} />
    </BottomSheet>
  )
}
