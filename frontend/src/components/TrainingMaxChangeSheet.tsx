import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { exercisesApi } from '@/api/fetcher'
import { BottomSheet } from '@/components/BottomSheet'
import { Button } from '@/components/dads/Button'
import { Input } from '@/components/dads/Input'

type ExerciseDetail = Awaited<ReturnType<typeof exercisesApi.get>>

type TrainingMaxChangeSheetProps = {
  open: boolean
  onClose: () => void
  exercise: ExerciseDetail['exercise']
  onChanged: (detail: ExerciseDetail) => void
}

function TrainingMaxChangeForm({ exercise, onClose, onChanged }: Omit<TrainingMaxChangeSheetProps, 'open'>) {
  const [value, setValue] = useState(exercise.current_training_max?.toString() ?? '')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)

  async function submitTrainingMax(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      onChanged(await exercisesApi.createTrainingMax(exercise.uid, { value: Number(value), reason }))
      onClose()
    } catch {
      toast.error('トレーニングマックスを変更できませんでした')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submitTrainingMax} className="flex flex-col gap-4">
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">トレーニングマックス (kg)</span>
        <Input
          type="number"
          inputMode="decimal"
          step="any"
          min={0}
          max={500}
          required
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">理由</span>
        <Input type="text" maxLength={255} required value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      <Button type="submit" size="lg" variant="solid-fill" aria-disabled={saving} className="w-full">
        {saving ? '保存中' : '変更する'}
      </Button>
    </form>
  )
}

export function TrainingMaxChangeSheet({ open, onClose, exercise, onChanged }: TrainingMaxChangeSheetProps) {
  return (
    <BottomSheet open={open} onClose={onClose} title="トレーニングマックスを変更">
      {open && <TrainingMaxChangeForm exercise={exercise} onClose={onClose} onChanged={onChanged} />}
    </BottomSheet>
  )
}
