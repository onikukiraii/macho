import { useState, type ReactElement, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Copy } from 'lucide-react'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { programImportsApi, programsApi, promptsApi } from '@/api/fetcher'
import { BackLink } from '@/components/BackLink'
import { Button } from '@/components/Button'
import { ErrorText } from '@/components/dads/ErrorText'
import { Textarea } from '@/components/dads/Textarea'
import { InputField } from '@/components/InputField'
import { Skeleton } from '@/components/ui/skeleton'
import { useCopyText } from '@/hooks/useCopyText'
import { useLoadable } from '@/hooks/useLoadable'
import { formatLocalDate } from '@/lib/dates'
import { readDraftJsonText, type ProgramDraftLocationState } from '@/lib/programDraftLocationState'

type DraftIssue = components['schemas']['DraftIssueResponse']
type PreviewCheck = { status: 'idle' } | { status: 'checking' } | { status: 'invalid'; issues: DraftIssue[] }

const RULES_FAILURE_MESSAGE = 'プログラム作成ルールを取得できませんでした'
const PROMPT_ITEMS = [
  'プログラム作成ルール',
  '種目一覧',
  '現在のトレーニングマックス',
  '直近4週の記録',
  '進行中のプログラムの設計メモ',
  'JSON の形',
]

function StepCard({ step, title, action, children }: { step: number; title: ReactNode; action?: ReactNode; children: ReactNode }): ReactElement {
  return (
    <li className="flex flex-col gap-3 rounded-8 bg-card p-3">
      <div className="flex items-center justify-between gap-4">
        <h2 className="flex items-center gap-2 text-std-18B-160">
          <span aria-hidden className="flex size-7 items-center justify-center rounded-full bg-primary text-dns-14B-130 text-primary-foreground">
            {step}
          </span>
          {title}
        </h2>
        {action}
      </div>
      {children}
    </li>
  )
}

function RulesSummary(): ReactElement {
  const [rules] = useLoadable(() => programsApi.rules(), [], RULES_FAILURE_MESSAGE)

  if (rules.status === 'loading') return <Skeleton className="h-28" />
  if (rules.status === 'failed') return <p className="text-muted-foreground">{RULES_FAILURE_MESSAGE}</p>
  if (rules.value.updated_at === null) return <p className="text-muted-foreground">ルールはまだありません</p>
  return (
    <>
      <pre className="line-clamp-4 whitespace-pre-wrap rounded-8 bg-background p-3 font-mono text-mono-14N-150">{rules.value.body}</pre>
      <p className="text-dns-14N-130 text-muted-foreground">{formatLocalDate(rules.value.updated_at)} 更新</p>
    </>
  )
}

function IssueList({ issues }: { issues: DraftIssue[] }): ReactElement {
  return (
    <div id="program-json-issues" className="flex flex-col gap-2">
      <ErrorText>{issues.length}件のエラーがあります。JSON を修正して、もう一度プレビューしてください</ErrorText>
      <ul className="flex flex-col gap-2">
        {issues.map((issue) => (
          <li key={`${issue.location}-${issue.message}`} className="flex flex-col gap-0.5 rounded-8 bg-background px-3 py-2">
            <span className="text-dns-14B-130">{issue.location}</span>
            <span className="text-std-16N-170">{issue.message}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ProgramCreatePage(): ReactElement {
  const navigate = useNavigate()
  const location = useLocation()
  const { copying, copyText } = useCopyText()
  const [jsonText, setJsonText] = useState(() => readDraftJsonText(location.state) ?? '')
  const [check, setCheck] = useState<PreviewCheck>({ status: 'idle' })

  const isEmpty = jsonText.trim() === ''

  async function previewProgram(): Promise<void> {
    if (isEmpty || check.status === 'checking') return
    setCheck({ status: 'checking' })
    try {
      const result = await programImportsApi.preview(jsonText)
      if (result.status === 'invalid') {
        setCheck({ status: 'invalid', issues: result.issues })
        return
      }
      const state: ProgramDraftLocationState = { jsonText }
      // プレビューから戻ったときに貼り付けた JSON を復元できるよう、いまの履歴にも残す
      navigate(location.pathname, { replace: true, state })
      navigate('/program/preview', { state })
    } catch {
      toast.error('プレビューできませんでした')
      setCheck({ status: 'idle' })
    }
  }

  return (
    <div className="flex flex-col gap-6 p-4">
      <BackLink to="/program">戻る</BackLink>
      <header className="flex flex-col gap-1">
        <h1 className="text-std-24B-150">プログラムの作成</h1>
        <p className="text-dns-14N-130 text-muted-foreground">Claude にプログラムを作成してもらい、返ってきた JSON を取り込みます</p>
      </header>
      <ol className="flex flex-col gap-3">
        <StepCard
          step={1}
          title="プログラム作成ルール"
          action={
            <Button asChild size="sm" variant="outline" className="shrink-0">
              <Link to="/program/rules">編集</Link>
            </Button>
          }
        >
          <RulesSummary />
        </StepCard>
        <StepCard step={2} title="生成用プロンプトをコピー">
          <p className="text-std-16N-170">
            次の内容をまとめてコピーします。claude.ai に貼り付け、「次の3週はベンチでスモロフ Jr」のように依頼を書き足してください。
          </p>
          <ul className="list-disc pl-5 text-dns-14N-130">
            {PROMPT_ITEMS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <Button
            size="lg"
            variant="outline"
            aria-disabled={copying}
            className="w-full"
            onClick={() =>
              copyText(async () => (await promptsApi.programGeneration()).text, {
                succeeded: 'プロンプトをコピーしました',
                failed: 'プロンプトをコピーできませんでした',
              })
            }
          >
            <Copy aria-hidden className="size-5" />
            プロンプトをコピー
          </Button>
        </StepCard>
        <StepCard step={3} title="返ってきた JSON を貼り付け">
          <InputField label="JSON">
            <Textarea
              rows={7}
              value={jsonText}
              isError={check.status === 'invalid'}
              aria-describedby={check.status === 'invalid' ? 'program-json-issues' : undefined}
              onChange={(event) => setJsonText(event.target.value)}
              className="w-full font-mono text-mono-14N-150"
            />
          </InputField>
          {check.status === 'invalid' && <IssueList issues={check.issues} />}
        </StepCard>
      </ol>
      <div className="flex flex-col gap-2">
        {isEmpty && <p className="text-dns-14N-130 text-muted-foreground">JSON を貼り付けるとプレビューできます</p>}
        <Button size="lg" variant="solid-fill" aria-disabled={isEmpty || check.status === 'checking'} className="w-full" onClick={previewProgram}>
          プレビュー
        </Button>
      </div>
    </div>
  )
}
