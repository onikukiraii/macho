import { useState, type ReactElement } from 'react'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { Textarea } from '@/components/dads/Textarea'
import { InputField } from '@/components/InputField'

type PerformedExerciseMemoFieldProps = {
  performedExercise: Pick<components['schemas']['PerformedExerciseResponse'], 'uid' | 'exercise_uid' | 'memo'>
}

export function PerformedExerciseMemoField({ performedExercise }: PerformedExerciseMemoFieldProps): ReactElement {
  const [memo, setMemo] = useState(performedExercise.memo)

  async function savePerformedExerciseMemo(): Promise<void> {
    try {
      await trainingLogsApi.updateExercise(performedExercise.uid, { exercise_uid: performedExercise.exercise_uid, memo })
    } catch {
      toast.error('メモを保存できませんでした')
    }
  }

  return (
    <InputField label="メモ">
      <Textarea
        rows={2}
        maxLength={1000}
        value={memo}
        onChange={(event) => setMemo(event.target.value)}
        onBlur={() => void savePerformedExerciseMemo()}
      />
    </InputField>
  )
}
