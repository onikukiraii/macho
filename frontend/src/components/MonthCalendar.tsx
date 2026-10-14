import type { ReactElement } from 'react'
import { format, parseISO } from 'date-fns'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { BODY_PART_LABEL, BODY_PART_ORDER, type BodyPart } from '@/api/constants'
import { BodyPartDot } from '@/components/BodyPartDot'
import { isAfterToday } from '@/lib/calendar'

const WEEKDAY_HEADERS = ['月', '火', '水', '木', '金', '土', '日']

type MonthCalendarProps = {
  year: number
  month: number
  /** `buildMonthGrid` が返す、前後の月の日を含めたマス目の日付 */
  dates: string[]
  today: string
  selectedDate: string
  /** 記録のある日付と、その日に鍛えた部位 */
  trainedBodyParts: ReadonlyMap<string, BodyPart[]>
  onSelectDate: (date: string) => void
  onShowPreviousMonth: () => void
  onShowNextMonth: () => void
}

export function MonthCalendar({
  year,
  month,
  dates,
  today,
  selectedDate,
  trainedBodyParts,
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
        {dates.map((date) => {
          const bodyParts = trainedBodyParts.get(date)
          return (
            <button
              key={date}
              type="button"
              aria-label={`${format(parseISO(date), 'M月d日')}${bodyParts === undefined ? '' : ` 記録あり${bodyParts.map((bodyPart) => ` ${BODY_PART_LABEL[bodyPart]}`).join('')}`}`}
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
              {bodyParts !== undefined && bodyParts.length === 0 && (
                <span aria-hidden className="size-1.5 rounded-full bg-current" />
              )}
              {bodyParts !== undefined && bodyParts.length > 0 && (
                <span className="flex gap-px">
                  {bodyParts.map((bodyPart) => (
                    <BodyPartDot key={bodyPart} bodyPart={bodyPart} />
                  ))}
                </span>
              )}
            </button>
          )
        })}
      </div>
      <ul aria-label="部位の色" className="flex flex-wrap justify-center gap-x-3 gap-y-1 text-dns-14N-120 text-muted-foreground">
        {BODY_PART_ORDER.map((bodyPart) => (
          <li key={bodyPart} className="flex items-center gap-1">
            <BodyPartDot bodyPart={bodyPart} />
            {BODY_PART_LABEL[bodyPart]}
          </li>
        ))}
      </ul>
    </section>
  )
}
