import { useState, type ReactElement } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { programImportsApi } from '@/api/fetcher'
import { WEEKDAY_LABEL } from '@/api/constants'
import { BackLink } from '@/components/BackLink'
import { Button } from '@/components/Button'
import { Disclosure, DisclosureSummary } from '@/components/dads/Disclosure'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { useNavigateBack } from '@/hooks/useNavigateBack'
import { formatDateString } from '@/lib/dates'
import { readDraftJsonText } from '@/lib/programDraftLocationState'

type ProgramPreview = components['schemas']['ProgramPreviewValidResponse']
type PreviewWeek = components['schemas']['PreviewWeekResponse']
type PreviewPlannedExercise = components['schemas']['PreviewPlannedExerciseResponse']

const LOAD_FAILURE_MESSAGE = 'プレビューを取得できませんでした'

function formatPlannedTarget(planned: PreviewPlannedExercise): string {
  const reps = planned.reps_max === null ? `${planned.reps}回` : `${planned.reps}〜${planned.reps_max}回`
  const intensity =
    planned.target_percent !== null ? ` ${planned.target_percent}%` : planned.target_rpe !== null ? ` RPE${planned.target_rpe}` : ''
  return `${reps} × ${planned.sets}セット${intensity}`
}

function NewExerciseBadge(): ReactElement {
  return <span className="rounded-4 bg-warning-orange-2 px-1.5 text-dns-14N-130 text-white">新規</span>
}

function PreviewWeekDays({ week }: { week: PreviewWeek }): ReactElement {
  return (
    <div className="flex flex-col divide-y divide-border">
      {week.days.map((day) => (
        <div key={day.day} className="flex flex-col py-2">
          <h3 className="flex items-baseline gap-2 text-std-16B-170">
            Day {day.day}
            <span className="text-dns-14N-130 text-muted-foreground">{WEEKDAY_LABEL[day.weekday]}曜日</span>
          </h3>
          <ul>
            {day.exercises.map((planned, index) => (
              <li key={index} className="flex items-baseline gap-3 py-1">
                <span className="flex flex-1 items-center gap-1.5 text-std-16N-170">
                  {planned.exercise_name}
                  {planned.is_new_exercise && <NewExerciseBadge />}
                </span>
                <span className="text-dns-14N-130 text-muted-foreground">{formatPlannedTarget(planned)}</span>
                <span className="text-std-16B-170">{planned.target_weight === null ? '-' : `${planned.target_weight} kg`}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function ProgramPreviewView({ jsonText, preview }: { jsonText: string; preview: ProgramPreview }): ReactElement {
  const navigate = useNavigate()
  const [importing, setImporting] = useState(false)

  async function importProgram(): Promise<void> {
    if (importing) return
    setImporting(true)
    try {
      await programImportsApi.create(jsonText)
      toast.success('プログラムを追加しました')
      navigate('/program', { replace: true })
    } catch {
      toast.error('プログラムを追加できませんでした')
      setImporting(false)
    }
  }

  return (
    <>
      <header className="flex flex-col gap-1">
        <p className="text-dns-14B-130 text-muted-foreground">プレビュー</p>
        <h1 className="text-std-24B-150">{preview.name}</h1>
        <p className="text-dns-14N-130 text-muted-foreground">
          {formatDateString(preview.start_date)} 開始 / 全{preview.weeks.length}週 / トレーニングマックスを
          {preview.tm_auto_update ? '自動更新する' : '自動更新しない'}
        </p>
      </header>
      {preview.design_note !== '' && (
        <Disclosure className="rounded-8 bg-card p-3">
          <DisclosureSummary className="text-std-16B-170">設計メモ</DisclosureSummary>
          <p className="whitespace-pre-wrap pt-2 text-dns-16N-130">{preview.design_note}</p>
        </Disclosure>
      )}
      {preview.new_exercises.length > 0 && (
        <section className="flex flex-col gap-2 rounded-8 bg-card p-3">
          <h2 className="text-std-18B-160">新しく作成する種目</h2>
          <ul className="flex flex-col divide-y divide-border">
            {preview.new_exercises.map((exercise) => (
              <li key={exercise.name} className="flex flex-col gap-1 py-2">
                <span className="flex items-center gap-2 text-std-16B-170">
                  {exercise.name}
                  <NewExerciseBadge />
                </span>
                <span className="text-dns-14N-130 text-muted-foreground">
                  {exercise.parent_name === null ? '' : `${exercise.parent_name} × ${exercise.coefficient} / `}
                  上げる幅 {exercise.increment_kg} kg / レスト {exercise.default_rest_seconds} 秒
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      <div className="flex flex-col gap-3">
        {preview.weeks.map((week, index) => (
          <Disclosure key={week.week} open={index === 0} className="rounded-8 bg-card p-3">
            <DisclosureSummary className="w-full items-center justify-between">
              <span className="flex items-baseline gap-2 text-std-18B-160">
                第{week.week}週<span className="text-dns-14N-130 text-muted-foreground">{week.label}</span>
              </span>
              <span className="text-dns-14N-130 text-muted-foreground">{week.days.length} 日</span>
            </DisclosureSummary>
            <PreviewWeekDays week={week} />
          </Disclosure>
        ))}
      </div>
      <div className="flex flex-col gap-3">
        <p className="rounded-8 bg-accent p-3 text-std-16N-170 text-accent-foreground">
          追加すると、進行中のプログラムは終了します。次の Day はこのプログラムの第1週 Day 1 になります。追加したプログラムはあとから変更できません。
        </p>
        <Button size="lg" variant="solid-fill" aria-disabled={importing} className="w-full" onClick={importProgram}>
          このプログラムを追加
        </Button>
      </div>
    </>
  )
}

function ProgramPreviewLoader({ jsonText }: { jsonText: string }): ReactElement {
  const [preview] = useLoadable(() => programImportsApi.preview(jsonText), [jsonText], LOAD_FAILURE_MESSAGE)

  if (preview.status === 'loading') return <Skeleton className="h-96" />
  if (preview.status === 'failed') return <p className="text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>
  if (preview.value.status === 'invalid') {
    return (
      <p className="text-muted-foreground">
        JSON にエラーがあります。<Link to="/program/new" className="text-primary underline">作成画面</Link>で確認してください
      </p>
    )
  }
  return <ProgramPreviewView jsonText={jsonText} preview={preview.value} />
}

export function ProgramPreviewPage(): ReactElement {
  const location = useLocation()
  const navigateBack = useNavigateBack()
  const jsonText = readDraftJsonText(location.state)

  if (jsonText === null) return <Navigate to="/program/new" replace />
  return (
    <div className="flex flex-col gap-6 p-4">
      <BackLink to="/program/new" onClick={navigateBack}>
        戻る
      </BackLink>
      <ProgramPreviewLoader jsonText={jsonText} />
    </div>
  )
}
