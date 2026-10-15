import { addDays, parseISO, subMonths, subYears } from 'date-fns'
import { toDateInputValue } from '@/lib/dates'

export type PeriodPreset = 'three_months' | 'six_months' | 'one_year' | 'all'

export const PERIOD_PRESETS: PeriodPreset[] = ['three_months', 'six_months', 'one_year', 'all']

export const PERIOD_PRESET_LABEL: Record<PeriodPreset, string> = {
  three_months: '直近3か月',
  six_months: '直近6か月',
  one_year: '直近1年',
  all: 'すべて',
}

export type ChartPoint = { x: number; y: number }
export type ChartRange = { min: number; max: number }
export type YAxisMode = 'zero' | 'fit'
export type LineAxes = { xRange: ChartRange; yRange: ChartRange; xTicks: number[] }

const ALL_PERIOD_START = '2000-01-01'
const NICE_STEPS = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8]

export function calculatePeriodStart(preset: PeriodPreset, today: string): string {
  const todayDate = parseISO(today)
  switch (preset) {
    case 'three_months':
      return toDateInputValue(addDays(subMonths(todayDate, 3), 1))
    case 'six_months':
      return toDateInputValue(addDays(subMonths(todayDate, 6), 1))
    case 'one_year':
      return toDateInputValue(addDays(subYears(todayDate, 1), 1))
    case 'all':
      return ALL_PERIOD_START
  }
}

export function calculateNiceMax(maxValue: number): number {
  if (maxValue <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(maxValue))
  for (const step of NICE_STEPS) {
    if (step * magnitude >= maxValue) return step * magnitude
  }
  return 10 * magnitude
}

export function scaleToHeight(value: number, { max, height }: { max: number; height: number }): number {
  return (value / max) * height
}

export function toStepPoints(points: ChartPoint[], { endX }: { endX: number }): ChartPoint[] {
  return points.flatMap((point, index) => {
    const nextX = index + 1 < points.length ? points[index + 1].x : endX
    return [point, { x: nextX, y: point.y }]
  })
}

const FIT_AXIS_STEP = 5

export function calculateLineAxes(points: ChartPoint[], { yAxis }: { yAxis: YAxisMode }): LineAxes | null {
  if (points.length === 0) return null
  const xs = points.map((point) => point.x)
  const ys = points.map((point) => point.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const maxY = Math.max(...ys)
  const yRange =
    yAxis === 'zero'
      ? { min: 0, max: calculateNiceMax(maxY) }
      : {
          min: Math.floor(Math.min(...ys) / FIT_AXIS_STEP) * FIT_AXIS_STEP,
          max: Math.ceil(maxY / FIT_AXIS_STEP) * FIT_AXIS_STEP + FIT_AXIS_STEP,
        }
  if (minX === maxX) return { xRange: { min: minX - 1, max: maxX + 1 }, yRange, xTicks: [minX] }
  return { xRange: { min: minX, max: maxX }, yRange, xTicks: [minX, Math.round((minX + maxX) / 2), maxX] }
}

export function formatKg(value: number): string {
  return `${value.toLocaleString('ja-JP', { maximumFractionDigits: 1 })} kg`
}

export function formatChangeRate(rate: number): string {
  const percent = Math.round(rate * 100)
  return `${percent >= 0 ? '+' : ''}${percent}%`
}

export function formatAxisValue(value: number): string {
  if (value >= 10000) return `${value / 10000}万`
  if (value >= 1000) return `${value / 1000}千`
  return String(value)
}
