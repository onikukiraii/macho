import { within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { TabLayout } from '@/layouts/TabLayout'
import { render, screen } from '@/test/utils'

describe('TabLayout', () => {
  it('下部のタブに、ホーム、プログラム、種目、分析、出力の5つが並ぶ', () => {
    window.history.pushState({}, '', '/')
    render(
      <Routes>
        <Route element={<TabLayout />}>
          <Route path="/" element={<p>ホーム画面</p>} />
        </Route>
      </Routes>,
    )

    const links = within(screen.getByRole('navigation', { name: 'メニュー' })).getAllByRole('link')
    expect(links.map((link) => link.textContent)).toEqual(['ホーム', 'プログラム', '種目', '分析', '出力'])
  })
})
