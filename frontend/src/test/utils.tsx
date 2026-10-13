import { render, type RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import type { ReactElement, ReactNode } from 'react'

function Providers({ children }: { children: ReactNode }) {
  return <BrowserRouter>{children}</BrowserRouter>
}

function customRender(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: Providers, ...options })
}

export { customRender as render }
export { screen, waitFor } from '@testing-library/react'
