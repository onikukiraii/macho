import { useState, type ReactElement } from 'react'
import { Copy } from 'lucide-react'
import { toast } from 'sonner'
import { promptsApi, trainingLogsApi } from '@/api/fetcher'
import { Button } from '@/components/Button'
import { ErrorText } from '@/components/dads/ErrorText'
import { Input } from '@/components/dads/Input'
import { InputField } from '@/components/InputField'
import { Skeleton } from '@/components/ui/skeleton'
import { useCopyText } from '@/hooks/useCopyText'
import { useLoadable } from '@/hooks/useLoadable'
import { defaultExportFromDate, toDateInputValue } from '@/lib/dates'

const COUNT_FAILURE_MESSAGE = 'セット件数を取得できませんでした'

function SetCount({ fromDate, toDate }: { fromDate: string; toDate: string }): ReactElement {
  const [count] = useLoadable(
    () => trainingLogsApi.exportCount({ from_date: fromDate, to_date: toDate }),
    [fromDate, toDate],
    COUNT_FAILURE_MESSAGE,
  )

  if (count.status === 'loading') return <Skeleton className="h-6 w-20" />
  if (count.status === 'failed') return <span className="text-std-16B-170">取得できませんでした</span>
  return <span className="text-std-16B-170">{count.value.count} セット</span>
}

export function ExportPage(): ReactElement {
  const [fromDate, setFromDate] = useState(() => defaultExportFromDate(new Date()))
  const [toDate, setToDate] = useState(() => toDateInputValue(new Date()))
  const [downloading, setDownloading] = useState(false)
  const { copying, copyText } = useCopyText()

  const rangeError = fromDate === '' || toDate === '' || fromDate > toDate

  async function downloadCsv(): Promise<void> {
    if (rangeError || downloading) return
    setDownloading(true)
    try {
      const blob = await trainingLogsApi.exportCsv({ from_date: fromDate, to_date: toDate })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `macho_${fromDate}_${toDate}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('CSV をダウンロードできませんでした')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-std-24B-150">出力</h1>
      <InputField label="開始日">
        <Input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
      </InputField>
      <InputField label="終了日">
        <Input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
      </InputField>
      {rangeError && <ErrorText>開始日は終了日以前の日付を指定してください</ErrorText>}
      <p className="flex items-center gap-2 text-std-16N-170">
        セット件数
        {rangeError ? <span className="text-std-16B-170">-</span> : <SetCount fromDate={fromDate} toDate={toDate} />}
      </p>
      <Button size="lg" variant="solid-fill" aria-disabled={rangeError || downloading} onClick={downloadCsv} className="w-full">
        CSV をダウンロード
      </Button>
      <section className="flex flex-col gap-3 border-t border-border pt-4">
        <h2 className="text-std-20B-150">月次レビュー</h2>
        <p className="text-std-16N-170">
          同じ期間の CSV に、プログラム作成ルール、設計メモ、トレーニングマックスの履歴を添えてコピーします。claude.ai
          に貼り付けると、この重量のままでよいかを相談できます。
        </p>
        <Button
          size="lg"
          variant="outline"
          aria-disabled={rangeError || copying}
          className="w-full"
          onClick={() => {
            if (rangeError) return
            void copyText(async () => (await promptsApi.review({ from_date: fromDate, to_date: toDate })).text, {
              succeeded: 'レビュー用プロンプトをコピーしました',
              failed: 'レビュー用プロンプトをコピーできませんでした',
            })
          }}
        >
          <Copy aria-hidden className="size-5" />
          レビュー用プロンプトをコピー
        </Button>
      </section>
    </div>
  )
}
