import createClient from 'openapi-fetch'
import type { paths } from './schema'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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

// --- Users ---

import type { components } from './schema'

type UserResponse = components['schemas']['UserResponse']
type UserCreateParams = components['schemas']['UserCreateParams']

export const usersApi = {
  list: async () => {
    const res = await api.GET('/users/')
    return unwrap<UserResponse[]>(res)
  },
  create: async (body: UserCreateParams) => {
    const res = await api.POST('/users/', { body })
    return unwrap<UserResponse>(res)
  },
}

export { api }
