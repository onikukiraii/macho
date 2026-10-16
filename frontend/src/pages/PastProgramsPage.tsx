import type { ReactElement } from 'react'
import { programsApi } from '@/api/fetcher'
import { BackLink } from '@/components/BackLink'
import { Disclosure, DisclosureSummary } from '@/components/dads/Disclosure'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { formatDateString } from '@/lib/dates'

const LOAD_FAILURE_MESSAGE = '過去のプログラムを取得できませんでした'

export function PastProgramsPage(): ReactElement {
  const [pastPrograms] = useLoadable(() => programsApi.past(), [], LOAD_FAILURE_MESSAGE)

  return (
    <div className="flex flex-col gap-6 p-4">
      <BackLink to="/program">戻る</BackLink>
      <h1 className="text-std-24B-150">過去のプログラム</h1>
      {pastPrograms.status === 'loading' && <Skeleton className="h-40" />}
      {pastPrograms.status === 'failed' && <p className="text-muted-foreground">{LOAD_FAILURE_MESSAGE}</p>}
      {pastPrograms.status === 'loaded' && pastPrograms.value.length === 0 && (
        <p className="text-muted-foreground">過去のプログラムはありません</p>
      )}
      {pastPrograms.status === 'loaded' && pastPrograms.value.length > 0 && (
        <ul className="flex flex-col gap-3">
          {pastPrograms.value.map((program) => (
            <li key={program.uid}>
              <article className="flex flex-col gap-2 rounded-8 bg-card p-3">
                <div className="flex flex-col gap-1">
                  <h2 className="text-std-18B-160">{program.name}</h2>
                  <p className="text-dns-14N-130 text-muted-foreground">
                    {formatDateString(program.start_date)} 〜 {formatDateString(program.end_date)} / 全{program.week_count}週
                  </p>
                </div>
                {program.design_note !== '' && (
                  <Disclosure className="border-t border-border pt-2">
                    <DisclosureSummary className="text-std-16B-170">設計メモ</DisclosureSummary>
                    <p className="whitespace-pre-wrap pt-2 text-dns-16N-130">{program.design_note}</p>
                  </Disclosure>
                )}
              </article>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
