import { useState, type MouseEvent, type ReactElement } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { BottomSheet } from '@/components/BottomSheet'
import { Button } from '@/components/dads/Button'
import { Textarea } from '@/components/dads/Textarea'
import { InputField } from '@/components/InputField'
import { PerformedExerciseCard } from '@/components/PerformedExerciseCard'
import { RestTimerBadge } from '@/components/RestTimerBadge'
import { RestTimerSheet } from '@/components/RestTimerSheet'
import { TrainingMaxNotice } from '@/components/TrainingMaxNotice'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { useRestTimer } from '@/hooks/useRestTimer'
import { formatDateString } from '@/lib/dates'
import { readTrainingMaxUpdates } from '@/lib/trainingLogLocationState'

type TrainingLogDetail = components['schemas']['TrainingLogDetailResponse']

const LOAD_FAILURE_MESSAGE = 'トレーニング記録を取得できませんでした'

function TrainingLogDeleteSheet({ uid, open, onClose }: { uid: string; open: boolean; onClose: () => void }): ReactElement {
  const navigate = useNavigate()
  const [deleting, setDeleting] = useState(false)

  async function deleteTrainingLog(): Promise<void> {
    if (deleting) return
    setDeleting(true)
    try {
      await trainingLogsApi.delete(uid)
      navigate('/', { replace: true })
    } catch {
      toast.error('トレーニング記録を削除できませんでした')
      setDeleting(false)
    }
  }

  return (
    <BottomSheet open={open} onClose={onClose} title="トレーニング記録を削除">
      <p className="text-std-16N-170">この記録の種目とセットも削除されます。</p>
      <div className="grid grid-cols-2 gap-4">
        <Button size="lg" variant="outline" onClick={onClose}>
          キャンセル
        </Button>
        <Button size="lg" variant="solid-fill" aria-disabled={deleting} onClick={() => void deleteTrainingLog()}>
          削除する
        </Button>
      </div>
    </BottomSheet>
  )
}

function UnsavedSetsLeaveSheet({ destination, onClose }: { destination: string; onClose: () => void }): ReactElement {
  const navigate = useNavigate()

  return (
    <BottomSheet open onClose={onClose} title="未保存のセットがあります">
      <p className="text-std-16N-170">移動すると、保存できなかったセットの入力は失われます。</p>
      <div className="grid grid-cols-2 gap-4">
        <Button size="lg" variant="outline" onClick={onClose}>
          キャンセル
        </Button>
        <Button size="lg" variant="solid-fill" onClick={() => navigate(destination)}>
          移動する
        </Button>
      </div>
    </BottomSheet>
  )
}

function TrainingLogMemoField({ trainingLog }: { trainingLog: TrainingLogDetail }): ReactElement {
  const [memo, setMemo] = useState(trainingLog.memo)

  async function saveTrainingLogMemo(): Promise<void> {
    try {
      await trainingLogsApi.update(trainingLog.uid, { memo })
    } catch {
      toast.error('メモを保存できませんでした')
    }
  }

  return (
    <InputField label="トレーニング記録のメモ">
      <Textarea
        rows={3}
        maxLength={1000}
        value={memo}
        onChange={(event) => setMemo(event.target.value)}
        onBlur={() => void saveTrainingLogMemo()}
      />
    </InputField>
  )
}

function TrainingLogView({ uid }: { uid: string }): ReactElement {
  const location = useLocation()
  const [trainingLog] = useLoadable(() => trainingLogsApi.get(uid), [uid], LOAD_FAILURE_MESSAGE)
  const [deleteSheetOpen, setDeleteSheetOpen] = useState(false)
  const restTimer = useRestTimer()
  const [restTimerSheetOpen, setRestTimerSheetOpen] = useState(false)
  const [unsavedExerciseUids, setUnsavedExerciseUids] = useState<ReadonlySet<string>>(new Set())
  const [leaveDestination, setLeaveDestination] = useState<string | null>(null)
  const trainingMaxUpdates = readTrainingMaxUpdates(location.state)

  function updateUnsavedExercise(performedUid: string, unsaved: boolean): void {
    setUnsavedExerciseUids((current) => {
      const next = new Set(current)
      if (unsaved) next.add(performedUid)
      else next.delete(performedUid)
      return next
    })
  }

  function confirmLeaveIfUnsaved(event: MouseEvent<HTMLAnchorElement>, to: string): void {
    if (unsavedExerciseUids.size === 0) return
    event.preventDefault()
    setLeaveDestination(to)
  }

  return (
    <div className="flex flex-col gap-4 p-4 pb-28">
      <Link to="/" onClick={(event) => confirmLeaveIfUnsaved(event, '/')} className="text-dns-14N-130 text-primary underline">
        ホームへ戻る
      </Link>
      <header className="flex items-start justify-between gap-4">
        {trainingLog.status === 'loaded' ? (
          <div className="flex flex-col gap-1">
            <h1 className="text-std-24B-150">{formatDateString(trainingLog.value.date)}</h1>
            <p className="text-dns-14N-130 text-muted-foreground">
              {trainingLog.value.day_label ?? '予定外のトレーニング'}
              {trainingLog.value.week_label !== null && ` ${trainingLog.value.week_label}`}
              {trainingLog.value.guide_date !== null && ` / 目安 ${formatDateString(trainingLog.value.guide_date)}`}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <Skeleton className="h-9 w-40" />
            <Skeleton className="h-5 w-32" />
          </div>
        )}
        <Button size="sm" variant="outline" onClick={() => setDeleteSheetOpen(true)}>
          記録を削除
        </Button>
      </header>
      {trainingMaxUpdates.length > 0 && <TrainingMaxNotice trainingMaxUpdates={trainingMaxUpdates} />}
      {trainingLog.status === 'loading' && <Skeleton className="h-60" />}
      {trainingLog.status === 'failed' && <p className="text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>}
      {trainingLog.status === 'loaded' && (
        <>
          {trainingLog.value.exercises.map((performedExercise) => (
            <PerformedExerciseCard
              key={performedExercise.uid}
              trainingLogUid={uid}
              performedExercise={performedExercise}
              onStartRest={(seconds, nextSetLabel) => {
                void restTimer.startRestTimer(seconds, nextSetLabel)
                setRestTimerSheetOpen(true)
              }}
              onUnsavedChange={(unsaved) => updateUnsavedExercise(performedExercise.uid, unsaved)}
              onNavigate={confirmLeaveIfUnsaved}
            />
          ))}
          <Button asChild size="lg" variant="outline">
            <Link
              to={`/training-logs/${uid}/exercise-picker`}
              onClick={(event) => confirmLeaveIfUnsaved(event, `/training-logs/${uid}/exercise-picker`)}
            >
              種目を追加
            </Link>
          </Button>
          <TrainingLogMemoField trainingLog={trainingLog.value} />
        </>
      )}
      <TrainingLogDeleteSheet uid={uid} open={deleteSheetOpen} onClose={() => setDeleteSheetOpen(false)} />
      {leaveDestination !== null && (
        <UnsavedSetsLeaveSheet destination={leaveDestination} onClose={() => setLeaveDestination(null)} />
      )}
      {restTimer.running !== null && (
        <>
          <div className="fixed inset-x-0 bottom-0 pb-[env(safe-area-inset-bottom)]">
            <div className="p-4">
              <RestTimerBadge
                remainingSeconds={restTimer.running.remainingSeconds}
                onOpen={() => setRestTimerSheetOpen(true)}
              />
            </div>
          </div>
          <RestTimerSheet
            open={restTimerSheetOpen}
            onClose={() => setRestTimerSheetOpen(false)}
            running={restTimer.running}
            notificationStatus={restTimer.notificationStatus}
            onExtend={restTimer.extendRestTimer}
            onStop={restTimer.stopRestTimer}
          />
        </>
      )}
    </div>
  )
}

export function TrainingLogPage(): ReactElement {
  const { uid } = useParams<{ uid: string }>()
  if (uid === undefined) return <p className="p-4 text-muted-foreground">トレーニング記録が見つかりません</p>
  return <TrainingLogView uid={uid} />
}
