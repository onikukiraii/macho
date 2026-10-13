import { format, subMonths } from 'date-fns'

const DATE_INPUT_FORMAT = 'yyyy-MM-dd'

/** タイムゾーン付きの日時を、端末のローカルの日付で表示する文字列にする */
export function formatLocalDate(dateTime: string): string {
  return format(new Date(dateTime), 'yyyy/MM/dd')
}

/** API の `YYYY-MM-DD` の日付を `yyyy/MM/dd` で表示する文字列にする。Date を経由しないためタイムゾーンでずれない */
export function formatDateString(date: string): string {
  return date.replaceAll('-', '/')
}

export function toDateInputValue(date: Date): string {
  return format(date, DATE_INPUT_FORMAT)
}

export function defaultExportFromDate(today: Date): string {
  return toDateInputValue(subMonths(today, 1))
}
