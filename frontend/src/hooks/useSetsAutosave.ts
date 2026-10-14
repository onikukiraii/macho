import { useRef, useState } from 'react'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { initializeColumns, isValidReps, isValidWeight, toSetParams, type SetColumn } from '@/lib/setColumns'

type PerformedExercise = components['schemas']['PerformedExerciseResponse']

export type SetsAutosave = {
  columns: SetColumn[]
  /** 画面の列だけを変える。入力中の値はまだ送らない */
  editColumns: (nextColumns: SetColumn[]) => void
  /** 画面の列を変えて、その種目の全セットを保存する */
  commitColumns: (nextColumns: SetColumn[]) => void
  saveFailed: boolean
  retrySave: () => void
}

/**
 * 種目のセットを自動保存する。送信中の要求は1本に限り、送信中に来た変更は最新の列を覚えて完了後に1回送る。
 * 全セットの置き換えなので、失敗したあとの送り直しは冪等になる
 */
export function useSetsAutosave(
  performedExercise: Pick<PerformedExercise, 'uid' | 'planned' | 'sets'>,
  onUnsavedChange: (unsaved: boolean) => void,
): SetsAutosave {
  const [columns, setColumns] = useState(() => initializeColumns(performedExercise))
  const [saveFailed, setSaveFailed] = useState(false)
  // 送信中か最後に送った内容。失敗したら null にして、次の保存で必ず送る
  const sentSetsKey = useRef<string | null>(JSON.stringify(toSetParams(columns)))
  const sending = useRef(false)
  const queuedColumns = useRef<SetColumn[] | null>(null)
  const saveFailedRef = useRef(false)
  const outOfRange = useRef(false)
  const notifiedUnsaved = useRef(false)

  function notifyUnsaved(): void {
    const unsaved = saveFailedRef.current || outOfRange.current || sending.current || queuedColumns.current !== null
    if (unsaved === notifiedUnsaved.current) return
    notifiedUnsaved.current = unsaved
    onUnsavedChange(unsaved)
  }

  function updateSaveFailed(failed: boolean): void {
    saveFailedRef.current = failed
    setSaveFailed(failed)
  }

  function sendColumns(nextColumns: SetColumn[]): void {
    if (sending.current) {
      queuedColumns.current = nextColumns
      notifyUnsaved()
      return
    }
    const sets = toSetParams(nextColumns)
    const setsKey = JSON.stringify(sets)
    if (setsKey === sentSetsKey.current) {
      notifyUnsaved()
      return
    }
    sending.current = true
    sentSetsKey.current = setsKey
    notifyUnsaved()
    trainingLogsApi
      .replaceSets(performedExercise.uid, { sets })
      .then(() => updateSaveFailed(false))
      .catch(() => {
        sentSetsKey.current = null
        updateSaveFailed(true)
      })
      .finally(() => {
        sending.current = false
        const queued = queuedColumns.current
        queuedColumns.current = null
        if (queued === null) notifyUnsaved()
        else sendColumns(queued)
      })
  }

  function saveColumns(nextColumns: SetColumn[]): void {
    outOfRange.current = nextColumns.some((column) => !isValidWeight(column.weight) || !isValidReps(column.reps))
    if (outOfRange.current) notifyUnsaved()
    else sendColumns(nextColumns)
  }

  function commitColumns(nextColumns: SetColumn[]): void {
    setColumns(nextColumns)
    saveColumns(nextColumns)
  }

  return {
    columns,
    editColumns: setColumns,
    commitColumns,
    saveFailed,
    retrySave: () => saveColumns(columns),
  }
}
