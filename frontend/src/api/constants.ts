import type { components } from './schema'

type Schemas = components['schemas']

export type ExerciseKind = Schemas['ExerciseKind']
export type DayStatus = Schemas['DayStatus']
export type Weekday = Schemas['Weekday']
export type Exercise = Schemas['ExerciseResponse']
export type ExerciseDetail = Schemas['ExerciseDetailResponse']
export type ExerciseHistoryEntry = Schemas['ExerciseHistoryEntryResponse']
export type ProgramWeekProgress = Schemas['ProgramWeekProgressResponse']
export type ProgramProgress = Schemas['ProgramProgressResponse']
export type RestTimerResponse = Schemas['RestTimerResponse']

export const EXERCISE_KIND_LABEL: Record<ExerciseKind, string> = {
  training_max: 'トレーニングマックスを持つ種目',
  derived: '派生種目',
  double_progression: 'ダブルプログレッションの種目',
}

export const DAY_STATUS_LABEL: Record<DayStatus, string> = {
  done: '消化済み',
  missed: '未実施',
  next: '次',
  pending: '未消化',
}

export const WEEKDAY_LABEL: Record<Weekday, string> = {
  mon: '月',
  tue: '火',
  wed: '水',
  thu: '木',
  fri: '金',
  sat: '土',
  sun: '日',
}
