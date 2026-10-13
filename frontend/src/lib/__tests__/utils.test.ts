import { describe, it, expect } from 'vitest'
import { cn } from '../utils'

describe('cn', () => {
  it('単一クラスをそのまま返す', () => {
    expect(cn('text-red-500')).toBe('text-red-500')
  })

  it('複数クラスを結合する', () => {
    expect(cn('px-4', 'py-2')).toBe('px-4 py-2')
  })

  it('競合するTailwindクラスをマージする', () => {
    expect(cn('px-4', 'px-8')).toBe('px-8')
  })

  it('条件付きクラスを処理する', () => {
    const isHidden = false
    expect(cn('base', isHidden && 'hidden', 'end')).toBe('base end')
  })

  it('undefinedやnullを無視する', () => {
    expect(cn('a', undefined, null, 'b')).toBe('a b')
  })
})
