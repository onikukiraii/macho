import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:37000'

const api = createClient<paths>({
  baseUrl: BASE_URL,
  fetch: async (input: Request) => {
    try {
      return await fetch(input)
    } catch {
      throw new Error('サーバーとの通信に失敗しました')
    }
  },
})

/** API レスポンスの data を取り出し、error があれば例外を投げる */
export function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.error !== undefined) {
    const err = result.error as Record<string, unknown>
    const message = typeof err.detail === 'string' ? err.detail : 'サーバーエラーが発生しました'
    throw new Error(message)
  }
  return result.data as T
}

type Schemas = components['schemas']

type DateRange = { from_date: string; to_date: string }

export const exercisesApi = {
  list: async () => unwrap<Schemas['ExerciseResponse'][]>(await api.GET('/api/exercises')),
  get: async (uid: string) =>
    unwrap<Schemas['ExerciseDetailResponse']>(await api.GET('/api/exercises/{uid}', { params: { path: { uid } } })),
  create: async (body: Schemas['ExerciseSaveParams']) =>
    unwrap<Schemas['ExerciseResponse']>(await api.POST('/api/exercises', { body })),
  update: async (uid: string, body: Schemas['ExerciseSaveParams']) =>
    unwrap<Schemas['ExerciseResponse']>(await api.PUT('/api/exercises/{uid}', { params: { path: { uid } }, body })),
  createTrainingMax: async (uid: string, body: Schemas['TrainingMaxCreateParams']) =>
    unwrap<Schemas['ExerciseDetailResponse']>(
      await api.POST('/api/exercises/{uid}/training-maxes', { params: { path: { uid } }, body }),
    ),
}

export const trainingLogsApi = {
  list: async (query: DateRange) =>
    unwrap<Schemas['TrainingLogSummaryResponse'][]>(await api.GET('/api/training-logs', { params: { query } })),
  latest: async () => unwrap<Schemas['TrainingLogSummaryResponse'] | null>(await api.GET('/api/training-logs/latest')),
  dayOptions: async () => unwrap<Schemas['DayOptionsResponse']>(await api.GET('/api/training-logs/day-options')),
  programProgress: async () =>
    unwrap<Schemas['ProgramProgressResponse'] | null>(await api.GET('/api/training-logs/program-progress')),
  exportCsv: async (query: DateRange) =>
    unwrap<Blob>(await api.GET('/api/training-logs/export', { params: { query }, parseAs: 'blob' })),
  exportCount: async (query: DateRange) =>
    unwrap<Schemas['SetCountResponse']>(await api.GET('/api/training-logs/export-count', { params: { query } })),
  byExercise: async (exerciseUid: string) =>
    unwrap<Schemas['ExerciseHistoryEntryResponse'][]>(
      await api.GET('/api/training-logs/by-exercise/{exercise_uid}', {
        params: { path: { exercise_uid: exerciseUid } },
      }),
    ),
  create: async (body: Schemas['TrainingLogCreateParams']) =>
    unwrap<Schemas['TrainingLogCreatedResponse']>(await api.POST('/api/training-logs', { body })),
  get: async (uid: string) =>
    unwrap<Schemas['TrainingLogDetailResponse']>(
      await api.GET('/api/training-logs/{uid}', { params: { path: { uid } } }),
    ),
  update: async (uid: string, body: Schemas['TrainingLogUpdateParams']) =>
    unwrap<Schemas['TrainingLogDetailResponse']>(
      await api.PATCH('/api/training-logs/{uid}', { params: { path: { uid } }, body }),
    ),
  delete: async (uid: string) => {
    unwrap(await api.DELETE('/api/training-logs/{uid}', { params: { path: { uid } } }))
  },
  addExercise: async (uid: string, body: Schemas['PerformedExerciseCreateParams']) =>
    unwrap<Schemas['TrainingLogDetailResponse']>(
      await api.POST('/api/training-logs/{uid}/exercises', { params: { path: { uid } }, body }),
    ),
  updateExercise: async (performedUid: string, body: Schemas['PerformedExerciseUpdateParams']) =>
    unwrap<Schemas['TrainingLogDetailResponse']>(
      await api.PUT('/api/training-logs/exercises/{performed_uid}', {
        params: { path: { performed_uid: performedUid } },
        body,
      }),
    ),
  replaceSets: async (performedUid: string, body: Schemas['SetsReplaceParams']) =>
    unwrap<Schemas['PerformedExerciseResponse']>(
      await api.PUT('/api/training-logs/exercises/{performed_uid}/sets', {
        params: { path: { performed_uid: performedUid } },
        body,
      }),
    ),
}

export const restTimerApi = {
  subscribe: async (body: Schemas['PushSubscriptionCreateParams']) => {
    unwrap(await api.POST('/api/rest-timer/push-subscriptions', { body }))
  },
  get: async () => unwrap<Schemas['RestTimerResponse'] | null>(await api.GET('/api/rest-timer')),
  start: async (body: Schemas['RestTimerStartParams']) =>
    unwrap<Schemas['RestTimerResponse']>(await api.POST('/api/rest-timer', { body })),
  extend: async (body: Schemas['RestTimerExtendParams']) =>
    unwrap<Schemas['RestTimerResponse']>(await api.POST('/api/rest-timer/extend', { body })),
  stop: async () => {
    unwrap(await api.DELETE('/api/rest-timer'))
  },
}

export { api }
