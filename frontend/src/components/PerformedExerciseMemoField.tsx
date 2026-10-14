import { useState, type ReactElement } from 'react'
import { Plus } from 'lucide-react'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { Textarea } from '@/components/dads/Textarea'
import { InputField } from '@/components/InputField'

type PerformedExerciseMemoFieldProps = {
  performedExercise: Pick<components['schemas']['PerformedExerciseResponse'], 'uid' | 'memo'>
}

export function PerformedExerciseMemoField({ performedExercise }: PerformedExerciseMemoFieldProps): ReactElement {
  const [memo, setMemo] = useState(performedExercise.memo)
  const [memoFieldOpen, setMemoFieldOpen] = useState(performedExercise.memo !== '')

  async function savePerformedExerciseMemo(): Promise<void> {
    try {
      await trainingLogsApi.updateExerciseMemo(performedExercise.uid, memo)
    } catch {
      toast.error('メモを保存できませんでした')
    }
  }

  if (!memoFieldOpen) {
    return (
      <button
        type="button"
        onClick={() => setMemoFieldOpen(true)}
        className="flex min-h-11 w-fit items-center gap-1 pr-2 text-dns-14N-130 text-primary"
      >
        <Plus aria-hidden className="size-5" />
        メモを追加
      </button>
    )
  }

  return (
    <InputField label="メモ">
      <Textarea
        autoFocus={performedExercise.memo === ''}
        rows={2}
        maxLength={1000}
        value={memo}
        onChange={(event) => setMemo(event.target.value)}
        onBlur={() => void savePerformedExerciseMemo()}
      />
    </InputField>
  )
}
