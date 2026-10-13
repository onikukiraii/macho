import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { trainingLogsApi } from '@/api/fetcher'
import { DAY_STATUS_LABEL, WEEKDAY_LABEL, type DayStatus } from '@/api/constants'
import { Skeleton } from '@/components/ui/skeleton'

type Progress = NonNullable<Awaited<ReturnType<typeof trainingLogsApi.programProgress>>>
type Week = Progress['weeks'][number]

function DayStatusBadge({ status }: { status: DayStatus }) {
  return (
    <span
      data-status={status}
      className="rounded-4 px-2 py-0.5 text-dns-14B-130 data-[status=done]:bg-success-2 data-[status=done]:text-white data-[status=missed]:bg-warning-orange-2 data-[status=missed]:text-black data-[status=next]:bg-key-900 data-[status=next]:text-white data-[status=pending]:bg-secondary data-[status=pending]:text-secondary-foreground"
    >
      {DAY_STATUS_LABEL[status]}
    </span>
  )
}

function WeekDays({ week }: { week: Week }) {
  return (
    <ul className="flex flex-col divide-y divide-border">
      {week.days.map((day) => {
        const row = (
          <>
            <span className="text-std-16B-170">
              Day {day.day}
              <span className="ml-2 text-dns-14N-130 text-muted-foreground">{WEEKDAY_LABEL[day.weekday]}曜日</span>
            </span>
            <DayStatusBadge status={day.status} />
          </>
        )
        return (
          <li key={day.program_day_uid}>
            {day.status === 'next' ? (
              <Link to="/?record=1" className="flex min-h-12 items-center justify-between gap-4 py-2">
                {row}
              </Link>
            ) : (
              <div className="flex min-h-12 items-center justify-between gap-4 py-2">{row}</div>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export function ProgramPage() {
  const [progress, setProgress] = useState<Progress | null | 'failed' | 'loading'>('loading')

  useEffect(() => {
    let cancelled = false
    trainingLogsApi
      .programProgress()
      .then((loaded) => !cancelled && setProgress(loaded))
      .catch(() => {
        if (cancelled) return
        toast.error('プログラムを取得できませんでした')
        setProgress('failed')
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (progress === 'loading') return <Skeleton className="m-4 h-60" />
  if (progress === 'failed') return <p className="p-4 text-muted-foreground">プログラムを取得できませんでした</p>
  if (progress === null) return <p className="p-4 text-muted-foreground">進行中のプログラムはありません</p>

  const nextWeek = progress.weeks.find((week) => week.days.some((day) => day.status === 'next'))?.week

  return (
    <div className="flex flex-col gap-6 p-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-std-24B-150">{progress.name}</h1>
        <p className="text-dns-14N-130 text-muted-foreground">
          {progress.start_date} 開始 / 全{progress.week_count}週
        </p>
      </header>
      {progress.design_note !== '' && <p className="whitespace-pre-wrap text-dns-16N-130">{progress.design_note}</p>}
      <div className="flex flex-col gap-3">
        {progress.weeks.map((week) => {
          const collapsed = nextWeek !== undefined && week.week > nextWeek
          if (!collapsed) {
            return (
              <section key={week.week} className="flex flex-col gap-1 rounded-8 bg-card p-3">
                <h2 className="text-std-18B-160">
                  第{week.week}週<span className="ml-2 text-dns-14N-130 text-muted-foreground">{week.label}</span>
                </h2>
                <WeekDays week={week} />
              </section>
            )
          }
          return (
            <details key={week.week} className="rounded-8 bg-card p-3">
              <summary className="flex cursor-pointer items-center justify-between gap-4">
                <span className="text-std-18B-160">
                  第{week.week}週<span className="ml-2 text-dns-14N-130 text-muted-foreground">{week.label}</span>
                </span>
                <span className="text-dns-14N-130 text-muted-foreground">
                  未消化 {week.days.filter((day) => day.status === 'pending').length} 日
                </span>
              </summary>
              <WeekDays week={week} />
            </details>
          )
        })}
      </div>
    </div>
  )
}
