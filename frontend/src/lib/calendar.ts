import { eachDayOfInterval, endOfMonth, endOfWeek, format, startOfWeek } from 'date-fns'
import { BODY_PART_ORDER, type BodyPart } from '@/api/constants'
import type { components } from '@/api/schema'

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

/** 記録のある日付ごとに、その日に鍛えた部位を部位の並び順で返す。同じ日の記録が複数あればまとめる */
export function indexTrainedBodyParts(
  summaries: Pick<components['schemas']['TrainingLogSummaryResponse'], 'date' | 'body_parts'>[],
): Map<string, BodyPart[]> {
  const index = new Map<string, BodyPart[]>()
  for (const summary of summaries) {
    const trained = new Set([...(index.get(summary.date) ?? []), ...summary.body_parts])
    index.set(
      summary.date,
      BODY_PART_ORDER.filter((bodyPart) => trained.has(bodyPart)),
    )
  }
  return index
}
