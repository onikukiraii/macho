import type { ReactElement } from 'react'
import { Link } from 'react-router-dom'
import { trainingLogsApi } from '@/api/fetcher'
import { DAY_STATUS_LABEL, WEEKDAY_LABEL, type DayStatus, type ProgramWeekProgress } from '@/api/constants'
import { Disclosure, DisclosureSummary } from '@/components/dads/Disclosure'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { formatDateString } from '@/lib/dates'

const LOAD_FAILURE_MESSAGE = 'プログラムを取得できませんでした'

function DayStatusBadge({ status }: { status: DayStatus }): ReactElement {
  return (
    <span
      data-status={status}
      className="rounded-4 px-2 py-0.5 text-dns-14B-130 data-[status=done]:bg-success-2 data-[status=done]:text-white data-[status=missed]:bg-warning-orange-2 data-[status=missed]:text-black data-[status=next]:bg-key-900 data-[status=next]:text-white data-[status=pending]:bg-secondary data-[status=pending]:text-secondary-foreground"
    >
      {DAY_STATUS_LABEL[status]}
    </span>
  )
}

function WeekDays({ week }: { week: ProgramWeekProgress }): ReactElement {
  return (
    <ul className="flex flex-col divide-y divide-border">
      {week.days.map((day) => {
        const row = (
          <>
            <span className="flex items-baseline gap-2 text-std-16B-170">
              Day {day.day}
              <span className="text-dns-14N-130 text-muted-foreground">{WEEKDAY_LABEL[day.weekday]}曜日</span>
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

function WeekTitle({ week }: { week: ProgramWeekProgress }): ReactElement {
  return (
    <span className="flex items-baseline gap-2 text-std-18B-160">
      第{week.week}週<span className="text-dns-14N-130 text-muted-foreground">{week.label}</span>
    </span>
  )
}

export function ProgramPage(): ReactElement {
  const [progress] = useLoadable(() => trainingLogsApi.programProgress(), [], LOAD_FAILURE_MESSAGE)

  if (progress.status === 'loading') {
    return (
      <div className="flex flex-col gap-6 p-4">
        <header className="flex flex-col gap-1">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-5 w-40" />
        </header>
        <Skeleton className="h-60" />
      </div>
    )
  }
  if (progress.status === 'failed') return <p className="p-4 text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>
  if (progress.value === null) return <p className="p-4 text-muted-foreground">進行中のプログラムはありません</p>

  const program = progress.value
  const nextWeek = program.weeks.find((week) => week.days.some((day) => day.status === 'next'))?.week

  return (
    <div className="flex flex-col gap-6 p-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-std-24B-150">{program.name}</h1>
        <p className="text-dns-14N-130 text-muted-foreground">
          {formatDateString(program.start_date)} 開始 / 全{program.week_count}週
        </p>
      </header>
      {program.design_note !== '' && <p className="whitespace-pre-wrap text-dns-16N-130">{program.design_note}</p>}
      <div className="flex flex-col gap-3">
        {program.weeks.map((week) => {
          const collapsed = nextWeek !== undefined && week.week > nextWeek
          if (!collapsed) {
            return (
              <section key={week.week} className="flex flex-col gap-1 rounded-8 bg-card p-3">
                <h2>
                  <WeekTitle week={week} />
                </h2>
                <WeekDays week={week} />
              </section>
            )
          }
          return (
            <Disclosure key={week.week} className="rounded-8 bg-card p-3">
              <DisclosureSummary className="w-full items-center justify-between">
                <WeekTitle week={week} />
                <span className="text-dns-14N-130 text-muted-foreground">
                  未消化 {week.days.filter((day) => day.status === 'pending').length} 日
                </span>
              </DisclosureSummary>
              <WeekDays week={week} />
            </Disclosure>
          )
        })}
      </div>
    </div>
  )
}
