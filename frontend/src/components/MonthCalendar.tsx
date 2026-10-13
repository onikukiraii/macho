import type { ReactElement } from 'react'
import { format, parseISO } from 'date-fns'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { buildMonthGrid, isAfterToday } from '@/lib/calendar'

const WEEKDAY_HEADERS = ['月', '火', '水', '木', '金', '土', '日']

type MonthCalendarProps = {
  year: number
  month: number
  today: string
  selectedDate: string
  recordedDates: ReadonlySet<string>
  onSelectDate: (date: string) => void
  onShowPreviousMonth: () => void
  onShowNextMonth: () => void
}

export function MonthCalendar({
  year,
  month,
  today,
  selectedDate,
  recordedDates,
  onSelectDate,
  onShowPreviousMonth,
  onShowNextMonth,
}: MonthCalendarProps): ReactElement {
  const monthPrefix = `${year}-${String(month).padStart(2, '0')}`

  return (
    <section aria-label="カレンダー" className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <button type="button" aria-label="前の月" onClick={onShowPreviousMonth} className="flex size-11 items-center justify-center">
          <ChevronLeft aria-hidden className="size-6" />
        </button>
        <h2 className="text-std-18B-160">
          {year}年{month}月
        </h2>
        <button type="button" aria-label="次の月" onClick={onShowNextMonth} className="flex size-11 items-center justify-center">
          <ChevronRight aria-hidden className="size-6" />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center">
        {WEEKDAY_HEADERS.map((weekday) => (
          <span key={weekday} className="text-dns-14N-120 text-muted-foreground">
            {weekday}
          </span>
        ))}
        {buildMonthGrid(year, month).map((date) => {
          const recorded = recordedDates.has(date)
          return (
            <button
              key={date}
              type="button"
              aria-label={`${format(parseISO(date), 'M月d日')}${recorded ? ' 記録あり' : ''}`}
              aria-pressed={date === selectedDate}
              disabled={isAfterToday(date, today)}
              onClick={() => onSelectDate(date)}
              className={
                date === selectedDate
                  ? 'flex h-11 flex-col items-center justify-center rounded-8 bg-primary text-std-16B-170 text-primary-foreground'
                  : date.startsWith(monthPrefix)
                    ? 'flex h-11 flex-col items-center justify-center rounded-8 text-std-16N-170 disabled:text-muted-foreground'
                    : 'flex h-11 flex-col items-center justify-center rounded-8 text-std-16N-170 text-muted-foreground'
              }
            >
              {parseISO(date).getDate()}
              {recorded && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
            </button>
          )
        })}
      </div>
    </section>
  )
}
