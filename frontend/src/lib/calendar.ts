import { eachDayOfInterval, endOfMonth, endOfWeek, format, startOfWeek } from 'date-fns'

/** 月曜始まりで、前後の月の日を含めた月のマス目の日付を `yyyy-MM-dd` で返す。month は 1〜12 */
export function buildMonthGrid(year: number, month: number): string[] {
  const firstDay = new Date(year, month - 1, 1)
  return eachDayOfInterval({
    start: startOfWeek(firstDay, { weekStartsOn: 1 }),
    end: endOfWeek(endOfMonth(firstDay), { weekStartsOn: 1 }),
  }).map((date) => format(date, 'yyyy-MM-dd'))
}

export function isAfterToday(date: string, today: string): boolean {
  return date > today
}
