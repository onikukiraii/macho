import { within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MonthCalendar } from '@/components/MonthCalendar'
import { buildMonthGrid } from '@/lib/calendar'
import { render, screen } from '@/test/utils'

function renderCalendar(trainedBodyParts: Map<string, ('chest' | 'back' | 'legs')[]>): void {
  render(
    <MonthCalendar
      year={2026}
      month={10}
      dates={buildMonthGrid(2026, 10)}
      today="2026-10-14"
      selectedDate="2026-10-14"
      trainedBodyParts={trainedBodyParts}
      onSelectDate={vi.fn()}
      onShowPreviousMonth={vi.fn()}
      onShowNextMonth={vi.fn()}
    />,
  )
}

describe('MonthCalendar', () => {
  it.each([
    { date: '2026-10-12', bodyParts: ['chest', 'back'] as const, label: '10月12日 記録あり 胸 背中' },
    { date: '2026-10-13', bodyParts: [] as const, label: '10月13日 記録あり' },
  ])('記録のある日は、その日に鍛えた部位を読み上げる: $label', ({ date, bodyParts, label }) => {
    renderCalendar(new Map([[date, [...bodyParts]]]))

    expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
  })

  it('部位の色の凡例を胸・背中・肩・腕・脚・腹の順に表示する', () => {
    renderCalendar(new Map())

    expect(
      within(screen.getByRole('list', { name: '部位の色' }))
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['胸', '背中', '肩', '腕', '脚', '腹'])
  })
})
