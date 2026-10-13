import { describe, it, expect } from 'vitest'
import { defaultExportFromDate, formatLocalDate } from '../dates'

describe('defaultExportFromDate', () => {
  it('月末の日付は1か月前の月末に丸める', () => {
    expect(defaultExportFromDate(new Date(2026, 2, 31))).toBe('2026-02-28')
  })
})

describe('formatLocalDate', () => {
  it('UTC の日時を端末のローカルの日付で表示する', () => {
    expect(formatLocalDate(new Date(2026, 9, 14, 23, 30).toISOString())).toBe('2026/10/14')
  })
})
