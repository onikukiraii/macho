import { describe, it, expect } from 'vitest'
import { defaultExportFromDate, formatDateString, formatLocalDate } from '../dates'

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

describe('formatDateString', () => {
  it('日付の文字列を端末のタイムゾーンに依らず yyyy/MM/dd で表示する', () => {
    expect(formatDateString('2026-10-01')).toBe('2026/10/01')
  })
})
