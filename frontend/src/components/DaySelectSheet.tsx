import { useState, type FormEvent, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import { toast } from 'sonner'
import type { components } from '@/api/schema'
import { WEEKDAY_LABEL } from '@/api/constants'
import { trainingLogsApi } from '@/api/fetcher'
import { BottomSheet } from '@/components/BottomSheet'
import { Button } from '@/components/dads/Button'
import { Input } from '@/components/dads/Input'
import { Radio } from '@/components/dads/Radio'
import { InputField } from '@/components/InputField'
import { Skeleton } from '@/components/ui/skeleton'
import type { Loadable } from '@/hooks/useLoadable'
import { formatDayLabel } from '@/lib/program'
import type { TrainingLogLocationState } from '@/lib/trainingLogLocationState'

type DayOption = components['schemas']['DayOptionResponse']

const DAY_OPTIONS_FAILURE_MESSAGE = 'Day の選択肢を取得できませんでした'

type DaySelectSheetProps = {
  open: boolean
  onClose: () => void
  initialDate: string
  today: string
  dayOptions: Loadable<components['schemas']['DayOptionsResponse']>
}

type DaySelectFormProps = { initialDate: string; today: string; options: DayOption[] }

function DaySelectForm({ initialDate, today, options }: DaySelectFormProps): ReactElement {
  const navigate = useNavigate()
  const [date, setDate] = useState(initialDate)
  const [programDayUid, setProgramDayUid] = useState<string | null>(
    options.find((option) => option.is_next)?.program_day_uid ?? null,
  )
  const [creating, setCreating] = useState(false)

  async function startTrainingLog(event: FormEvent): Promise<void> {
    event.preventDefault()
    if (creating) return
    setCreating(true)
    try {
      const created = await trainingLogsApi.create({ date, program_day_uid: programDayUid })
      const state: TrainingLogLocationState = { trainingMaxUpdates: created.training_max_updates }
      navigate(`/training-logs/${created.uid}`, { state, replace: true })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'トレーニング記録を作成できませんでした')
      setCreating(false)
    }
  }

  return (
    <form onSubmit={startTrainingLog} className="flex flex-col gap-4">
      <InputField label="日付">
        <Input type="date" required max={today} value={date} onChange={(event) => setDate(event.target.value)} />
      </InputField>
      <fieldset className="flex flex-col dark:[&_label>span:last-child]:text-solid-gray-50">
        <legend className="text-std-16B-170">Day</legend>
        {options.map((option) => (
          <Radio
            key={option.program_day_uid}
            name="program-day"
            checked={programDayUid === option.program_day_uid}
            onChange={() => setProgramDayUid(option.program_day_uid)}
          >
            {formatDayLabel(option)} {WEEKDAY_LABEL[option.weekday]}曜日
            {option.is_next && ' 次'}
            {option.last_recorded_on !== null && ` 記録済み ${format(parseISO(option.last_recorded_on), 'M/d')}`}
          </Radio>
        ))}
        <Radio name="program-day" checked={programDayUid === null} onChange={() => setProgramDayUid(null)}>
          予定外のトレーニング
        </Radio>
      </fieldset>
      <Button type="submit" size="lg" variant="solid-fill" aria-disabled={creating} className="w-full">
        {creating ? '作成中' : '記録を開始'}
      </Button>
    </form>
  )
}

export function DaySelectSheet({ open, onClose, initialDate, today, dayOptions }: DaySelectSheetProps): ReactElement {
  return (
    <BottomSheet open={open} onClose={onClose} title="記録を追加">
      {dayOptions.status === 'loading' && <Skeleton className="h-60" />}
      {dayOptions.status === 'failed' && (
        <>
          <p className="text-muted-foreground">{DAY_OPTIONS_FAILURE_MESSAGE}</p>
          <DaySelectForm initialDate={initialDate} today={today} options={[]} />
        </>
      )}
      {dayOptions.status === 'loaded' && (
        <DaySelectForm initialDate={initialDate} today={today} options={dayOptions.value.options} />
      )}
    </BottomSheet>
  )
}
