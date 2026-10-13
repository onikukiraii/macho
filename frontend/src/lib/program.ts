import type { components } from '@/api/schema'

export function formatDayLabel(day: Pick<components['schemas']['DayOptionResponse'], 'week' | 'day'>): string {
  return `第${day.week}週 Day${day.day}`
}
