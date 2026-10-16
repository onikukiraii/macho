import { fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { programImportsApi, programsApi, promptsApi } from '@/api/fetcher'
import { Toaster } from '@/components/ui/sonner'
import { ProgramCreatePage } from '@/pages/ProgramCreatePage'
import { render, screen, waitFor } from '@/test/utils'

vi.mock('@/api/fetcher', () => ({
  programsApi: { rules: vi.fn() },
  promptsApi: { programGeneration: vi.fn() },
  programImportsApi: { preview: vi.fn() },
}))

class FakeClipboardItem {
  readonly items: Record<string, Promise<Blob>>

  constructor(items: Record<string, Promise<Blob>>) {
    this.items = items
  }
}

const writeClipboard = vi.fn<(items: FakeClipboardItem[]) => Promise<void>>()

beforeEach(() => {
  vi.mocked(programsApi.rules).mockResolvedValue({ body: '## 目標\nBIG3 合計 400kg', updated_at: '2026-10-02T03:00:00Z' })
  vi.stubGlobal('ClipboardItem', FakeClipboardItem)
  Object.defineProperty(navigator, 'clipboard', { value: { write: writeClipboard }, configurable: true })
  writeClipboard.mockResolvedValue()
})

afterEach(() => {
  vi.resetAllMocks()
  vi.unstubAllGlobals()
})

function renderProgramCreatePage(): void {
  window.history.pushState({}, '', '/program/new')
  render(
    <>
      <Routes>
        <Route path="/program/new" element={<ProgramCreatePage />} />
        <Route path="/program/preview" element={<p>プレビュー画面</p>} />
      </Routes>
      <Toaster />
    </>,
  )
}

function pasteAndPreview(): void {
  fireEvent.change(screen.getByRole('textbox', { name: 'JSON' }), { target: { value: '{"name": "ベンチ スモロフ Jr"}' } })
  fireEvent.click(screen.getByRole('button', { name: 'プレビュー' }))
}

describe('ProgramCreatePage', () => {
  it('エラーの無い JSON を貼ってプレビューを押すと、プレビュー画面へ移る', async () => {
    vi.mocked(programImportsApi.preview).mockResolvedValue({
      status: 'valid',
      name: 'ベンチ スモロフ Jr',
      start_date: '2026-10-19',
      tm_auto_update: false,
      design_note: '',
      new_exercises: [],
      weeks: [],
    })
    renderProgramCreatePage()

    pasteAndPreview()

    expect(await screen.findByText('プレビュー画面')).toBeInTheDocument()
  })

  it('エラーがあると、件数とエラーの一覧を表示し、プレビュー画面へは移らない', async () => {
    vi.mocked(programImportsApi.preview).mockResolvedValue({
      status: 'invalid',
      issues: [
        { location: '第2週 Day 3「ポーズベンチ」', message: 'target_rpe と target_percent の両方が設定されています' },
        { location: 'new_exercises「ケーブルフライ」', message: 'default_rest_seconds が設定されていません' },
      ],
    })
    renderProgramCreatePage()

    pasteAndPreview()

    expect(await screen.findByText('2件のエラーがあります。JSON を修正して、もう一度プレビューしてください')).toBeInTheDocument()
    expect(screen.getByText('第2週 Day 3「ポーズベンチ」')).toBeInTheDocument()
    expect(screen.queryByText('プレビュー画面')).not.toBeInTheDocument()
  })

  it('プロンプトをコピーを押すと、取得したプロンプトをクリップボードへ書く', async () => {
    vi.mocked(promptsApi.programGeneration).mockResolvedValue({ text: '次のルールと記録をもとに' })
    renderProgramCreatePage()

    fireEvent.click(screen.getByRole('button', { name: 'プロンプトをコピー' }))

    await waitFor(() => expect(writeClipboard).toHaveBeenCalled())
    const [item] = writeClipboard.mock.calls[0][0]
    expect(await (await item.items['text/plain']).text()).toBe('次のルールと記録をもとに')
  })

  it('プロンプトをコピーすると、コピーしたことをトーストで表示する', async () => {
    vi.mocked(promptsApi.programGeneration).mockResolvedValue({ text: '次のルールと記録をもとに' })
    renderProgramCreatePage()

    fireEvent.click(screen.getByRole('button', { name: 'プロンプトをコピー' }))

    expect(await screen.findByText('プロンプトをコピーしました')).toBeInTheDocument()
  })
})

describe('ProgramCreatePage の貼り付け欄', () => {
  it('プレビュー画面から戻ると、貼り付けた JSON が残っている', async () => {
    window.history.pushState({ usr: { jsonText: '{"name": "ベンチ スモロフ Jr"}' }, key: 'create', idx: 0 }, '', '/program/new')
    render(
      <Routes>
        <Route path="/program/new" element={<ProgramCreatePage />} />
      </Routes>,
    )

    expect(await screen.findByRole('textbox', { name: 'JSON' })).toHaveValue('{"name": "ベンチ スモロフ Jr"}')
  })
})
