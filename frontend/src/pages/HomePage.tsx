import { useState, type ReactElement } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { addMonths, format, parseISO } from 'date-fns'
import { Plus } from 'lucide-react'
import type { components } from '@/api/schema'
import { trainingLogsApi } from '@/api/fetcher'
import { Button } from '@/components/Button'
import { DaySelectSheet } from '@/components/DaySelectSheet'
import { MonthCalendar } from '@/components/MonthCalendar'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { useToday } from '@/hooks/useToday'
import { buildMonthGrid, indexTrainedBodyParts } from '@/lib/calendar'
import { formatDateString } from '@/lib/dates'
import { formatSet } from '@/lib/exercises'
import { formatDayLabel } from '@/lib/program'

type TrainingLogSummary = components['schemas']['TrainingLogSummaryResponse']

const LOGS_FAILURE_MESSAGE = 'トレーニング記録を取得できませんでした'
const LATEST_FAILURE_MESSAGE = '直近の記録を取得できませんでした'
const DAY_OPTIONS_FAILURE_MESSAGE = 'Day の選択肢を取得できませんでした'

function TrainingLogSummaryLink({ summary }: { summary: TrainingLogSummary }): ReactElement {
  return (
    <Link to={`/training-logs/${summary.uid}`} className="flex flex-col gap-1 rounded-8 bg-card p-3">
      <span className="flex items-baseline gap-2 text-std-16B-170">
        {formatDateString(summary.date)}
        <span className="text-dns-14N-130 text-muted-foreground">{summary.day_label ?? '予定外のトレーニング'}</span>
      </span>
      <ul className="text-dns-14N-130">
        {summary.top_sets.map((topSet) => (
          <li key={topSet.exercise_name}>
            {topSet.exercise_name} {formatSet(topSet)}
          </li>
        ))}
      </ul>
    </Link>
  )
}

export function HomePage(): ReactElement {
  const today = useToday()
  // null は今日を指す。日をまたいだときに、選んでいる日と表示している月も新しい今日へ移すため
  const [pickedDate, setPickedDate] = useState<string | null>(null)
  const [shownMonth, setShownMonth] = useState<{ year: number; month: number } | null>(null)
  const selectedDate = pickedDate ?? today
  const { year, month } = shownMonth ?? { year: parseISO(today).getFullYear(), month: parseISO(today).getMonth() + 1 }
  const [searchParams, setSearchParams] = useSearchParams()
  const daySelectOpen = searchParams.get('record') === '1'

  const grid = buildMonthGrid(year, month)
  const fromDate = grid[0]
  const toDate = grid[grid.length - 1]
  const [trainingLogs] = useLoadable(
    () => trainingLogsApi.list({ from_date: fromDate, to_date: toDate }),
    [fromDate, toDate],
    LOGS_FAILURE_MESSAGE,
  )
  const [latest] = useLoadable(() => trainingLogsApi.latest(), [], LATEST_FAILURE_MESSAGE)
  const [dayOptions] = useLoadable(() => trainingLogsApi.dayOptions(), [], DAY_OPTIONS_FAILURE_MESSAGE)

  const recordedDates = new Set(trainingLogs.status === 'loaded' ? trainingLogs.value.map((summary) => summary.date) : [])
  const nextDay = dayOptions.status === 'loaded' ? dayOptions.value.options.find((option) => option.is_next) : undefined

  function showMonth(monthOffset: number): void {
    const shown = addMonths(new Date(year, month - 1, 1), monthOffset)
    setShownMonth({ year: shown.getFullYear(), month: shown.getMonth() + 1 })
  }

  function openDaySelect(): void {
    setSearchParams({ record: '1' })
  }

  return (
    <div className="flex flex-col gap-6 px-4 pt-4 pb-20">
      <h1 className="text-std-24B-150">ホーム</h1>
      <MonthCalendar
        year={year}
        month={month}
        dates={grid}
        today={today}
        selectedDate={selectedDate}
        trainedBodyParts={indexTrainedBodyParts(trainingLogs.status === 'loaded' ? trainingLogs.value : [])}
        onSelectDate={(date) => setPickedDate(date === today ? null : date)}
        onShowPreviousMonth={() => showMonth(-1)}
        onShowNextMonth={() => showMonth(1)}
      />
      {selectedDate === today && (
        <section className="flex items-center justify-between gap-4 rounded-8 bg-card p-3">
          <div className="flex flex-col gap-1">
            <h2 className="text-dns-14N-130 text-muted-foreground">次の Day</h2>
            {dayOptions.status === 'loading' && <Skeleton className="h-6 w-32" />}
            {dayOptions.status === 'failed' && <p className="text-std-16B-170">-</p>}
            {dayOptions.status === 'loaded' && (
              <p className="text-std-16B-170">
                {nextDay === undefined ? 'ありません' : formatDayLabel(nextDay)}
              </p>
            )}
          </div>
          <Button size="md" variant="solid-fill" onClick={openDaySelect}>
            記録する
          </Button>
        </section>
      )}
      {grid.includes(selectedDate) && (
        <section className="flex flex-col gap-2">
          <h2 className="text-std-18B-160">{format(parseISO(selectedDate), 'M月d日')}の記録</h2>
          {trainingLogs.status === 'loading' && <Skeleton className="h-20" />}
          {trainingLogs.status === 'failed' && <p className="text-muted-foreground">{LOGS_FAILURE_MESSAGE}</p>}
          {trainingLogs.status === 'loaded' && !recordedDates.has(selectedDate) && (
            <p className="text-muted-foreground">記録はありません</p>
          )}
          {trainingLogs.status === 'loaded' &&
            trainingLogs.value
              .filter((summary) => summary.date === selectedDate)
              .map((summary) => <TrainingLogSummaryLink key={summary.uid} summary={summary} />)}
        </section>
      )}
      <section className="flex flex-col gap-2">
        <h2 className="text-std-18B-160">直近の記録</h2>
        {latest.status === 'loading' && <Skeleton className="h-20" />}
        {latest.status === 'failed' && <p className="text-muted-foreground">{LATEST_FAILURE_MESSAGE}</p>}
        {latest.status === 'loaded' && latest.value === null && <p className="text-muted-foreground">記録はありません</p>}
        {latest.status === 'loaded' && latest.value !== null && <TrainingLogSummaryLink summary={latest.value} />}
      </section>
      <button
        type="button"
        aria-label="記録を追加"
        onClick={openDaySelect}
        className="fixed right-4 bottom-[calc(5rem+env(safe-area-inset-bottom))] flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg"
      >
        <Plus aria-hidden className="size-7" />
      </button>
      <DaySelectSheet
        open={daySelectOpen}
        onClose={() => setSearchParams({})}
        initialDate={selectedDate}
        today={today}
        dayOptions={dayOptions}
      />
    </div>
  )
}
