import { useState, type ReactElement } from 'react'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { programsApi } from '@/api/fetcher'
import { BackLink } from '@/components/BackLink'
import { Button } from '@/components/Button'
import { Textarea } from '@/components/dads/Textarea'
import { InputField } from '@/components/InputField'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { useNavigateBack } from '@/hooks/useNavigateBack'
import { formatLocalDate } from '@/lib/dates'

type ProgramRules = components['schemas']['ProgramRulesResponse']

const LOAD_FAILURE_MESSAGE = 'プログラム作成ルールを取得できませんでした'
const RULES_MAX_LENGTH = 16000

function ProgramRulesForm({ initialRules }: { initialRules: ProgramRules }): ReactElement {
  const [body, setBody] = useState(initialRules.body)
  const [updatedAt, setUpdatedAt] = useState(initialRules.updated_at)
  const [saving, setSaving] = useState(false)

  async function saveProgramRules(): Promise<void> {
    if (saving) return
    setSaving(true)
    try {
      const saved = await programsApi.saveRules({ body })
      setUpdatedAt(saved.updated_at)
      toast.success('プログラム作成ルールを保存しました')
    } catch {
      toast.error('プログラム作成ルールを保存できませんでした')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <InputField label="本文">
        <Textarea
          rows={16}
          value={body}
          maxLength={RULES_MAX_LENGTH}
          onChange={(event) => setBody(event.target.value)}
          className="w-full font-mono text-mono-14N-150"
        />
      </InputField>
      {updatedAt !== null && <p className="text-dns-14N-130 text-muted-foreground">{formatLocalDate(updatedAt)} 更新</p>}
      <Button size="lg" variant="solid-fill" aria-disabled={saving} className="w-full" onClick={saveProgramRules}>
        保存
      </Button>
    </>
  )
}

export function ProgramRulesPage(): ReactElement {
  const [rules] = useLoadable(() => programsApi.rules(), [], LOAD_FAILURE_MESSAGE)
  const navigateBack = useNavigateBack()

  return (
    <div className="flex flex-col gap-4 p-4">
      <BackLink to="/program/new" onClick={navigateBack}>
        戻る
      </BackLink>
      <header className="flex flex-col gap-1">
        <h1 className="text-std-24B-150">プログラム作成ルール</h1>
        <p className="text-dns-14N-130 text-muted-foreground">
          生成用プロンプトの先頭に挿入されます。アプリはこの内容を解釈せず、そのまま Claude に渡します
        </p>
      </header>
      {rules.status === 'loading' && <Skeleton className="h-96" />}
      {rules.status === 'failed' && <p className="text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>}
      {rules.status === 'loaded' && <ProgramRulesForm initialRules={rules.value} />}
    </div>
  )
}
