import { describe, it, expect } from 'vitest'
import { resolveReturnTo } from '../returnTo'

const ORIGIN = 'https://macho.example'

describe('resolveReturnTo', () => {
  it.each(['//evil.example', '/\t/evil.example', '/\\evil.example', 'https://evil.example/path'])(
    '他の origin へ遷移する値 %j は採用しない',
    (value) => {
      expect(resolveReturnTo(value, ORIGIN)).toBeNull()
    },
  )

  it('同じ origin のパスはクエリとハッシュを残し、追加のパラメータを付ける', () => {
    expect(resolveReturnTo('/training-logs/new?a=1#top', ORIGIN, { createdExerciseUid: 'u1' })).toBe(
      '/training-logs/new?a=1&createdExerciseUid=u1#top',
    )
  })
})
