import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { trainingLogsApi } from '@/api/fetcher'
import { Button } from '@/components/dads/Button'
import { Input } from '@/components/dads/Input'

function localDateString(date: Date): string {
  return date.toLocaleDateString('sv-SE')
}

function defaultFromDate(): string {
  const date = new Date()
  date.setMonth(date.getMonth() - 1)
  return localDateString(date)
}

export function ExportPage() {
  const [fromDate, setFromDate] = useState(defaultFromDate)
  const [toDate, setToDate] = useState(() => localDateString(new Date()))
  const [counted, setCounted] = useState<{ fromDate: string; toDate: string; count: number | null } | null>(null)
  const [downloading, setDownloading] = useState(false)

  const rangeError = fromDate === '' || toDate === '' || fromDate > toDate

  useEffect(() => {
    if (rangeError) return
    let cancelled = false
    trainingLogsApi
      .exportCount({ from_date: fromDate, to_date: toDate })
      .then(({ count }) => !cancelled && setCounted({ fromDate, toDate, count }))
      .catch(() => {
        if (cancelled) return
        toast.error('セット件数を取得できませんでした')
        setCounted({ fromDate, toDate, count: null })
      })
    return () => {
      cancelled = true
    }
  }, [fromDate, toDate, rangeError])

  async function downloadCsv() {
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

  const countLabel = (() => {
    if (rangeError) return '-'
    if (counted?.fromDate !== fromDate || counted.toDate !== toDate) return '取得中'
    return counted.count === null ? '取得できませんでした' : `${counted.count} セット`
  })()

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-std-24B-150">出力</h1>
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">開始日</span>
        <Input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-std-16B-170">終了日</span>
        <Input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
      </label>
      {rangeError && <p className="text-error-2">開始日は終了日以前の日付を指定してください</p>}
      <p className="text-std-16N-170">
        セット件数<span className="ml-2 text-std-16B-170">{countLabel}</span>
      </p>
      <Button size="lg" variant="solid-fill" aria-disabled={rangeError || downloading} onClick={downloadCsv} className="w-full">
        CSV をダウンロード
      </Button>
    </div>
  )
}
