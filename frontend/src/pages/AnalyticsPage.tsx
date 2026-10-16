import { useState, type ReactElement, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { addDays, differenceInCalendarDays, format, parseISO } from 'date-fns'
import type { components } from '@/api/schema'
import { analyticsApi, exercisesApi } from '@/api/fetcher'
import { BODY_PART_LABEL, type BodyPart } from '@/api/constants'
import { Select } from '@/components/dads/Select'
import { Tab, TabItem, TabList } from '@/components/dads/Tab'
import { InputField } from '@/components/InputField'
import { LineChart } from '@/components/LineChart'
import { StackedBarChart, type VolumeBars } from '@/components/StackedBarChart'
import { Skeleton } from '@/components/ui/skeleton'
import { useLoadable } from '@/hooks/useLoadable'
import { useToday } from '@/hooks/useToday'
import {
  PERIOD_PRESETS,
  PERIOD_PRESET_LABEL,
  calculatePeriodStart,
  formatAxisValue,
  formatChangeRate,
  formatKg,
  toStepPoints,
  type PeriodPreset,
} from '@/lib/analytics'

type AnalyticsTab = 'overview' | 'exercise'
type BucketUnit = 'week' | 'month'
type Overview = components['schemas']['OverviewResponse']
type VolumeBucket = components['schemas']['VolumeBucketResponse']
type BodyPartVolume = components['schemas']['BodyPartVolumeResponse']
type ExerciseVolumeBucket = components['schemas']['ExerciseVolumeBucketResponse']

const OVERVIEW_FAILURE_MESSAGE = '分析を取得できませんでした'
const EXERCISES_FAILURE_MESSAGE = '種目の一覧を取得できませんでした'
const EXERCISE_FAILURE_MESSAGE = '種目の分析を取得できませんでした'
const BUCKET_UNIT_LABEL: Record<BucketUnit, string> = { week: '週', month: '月' }
const EPOCH = parseISO('1970-01-01')

function toEpochDay(date: string): number {
  return differenceInCalendarDays(parseISO(date), EPOCH)
}

function formatEpochDay(epochDay: number): string {
  return format(addDays(EPOCH, epochDay), 'M/d')
}

function formatBucketLabel(start: string, unit: BucketUnit): string {
  return unit === 'week' ? format(parseISO(start), 'M/d') : `${parseISO(start).getMonth() + 1}月`
}

function PeriodField({ preset, onChange }: { preset: PeriodPreset; onChange: (preset: PeriodPreset) => void }): ReactElement {
  return (
    <InputField label="期間">
      <Select
        value={preset}
        onChange={(event) => {
          const selected = PERIOD_PRESETS.find((candidate) => candidate === event.target.value)
          if (selected !== undefined) onChange(selected)
        }}
      >
        {PERIOD_PRESETS.map((candidate) => (
          <option key={candidate} value={candidate}>
            {PERIOD_PRESET_LABEL[candidate]}
          </option>
        ))}
      </Select>
    </InputField>
  )
}

function BucketUnitToggle({ unit, onChange }: { unit: BucketUnit; onChange: (unit: BucketUnit) => void }): ReactElement {
  return (
    <div role="group" aria-label="集計の単位" className="flex overflow-hidden rounded-6 border border-primary">
      {(['week', 'month'] as const).map((candidate) => (
        <button
          key={candidate}
          type="button"
          aria-pressed={unit === candidate}
          onClick={() => onChange(candidate)}
          className={
            unit === candidate
              ? 'min-h-9 min-w-13 bg-primary text-oln-16B-100 text-primary-foreground'
              : 'min-h-9 min-w-13 bg-card text-oln-16B-100 text-primary'
          }
        >
          {BUCKET_UNIT_LABEL[candidate]}
        </button>
      ))}
    </div>
  )
}

function Card({ children }: { children: ReactNode }): ReactElement {
  return <section className="flex flex-col gap-2 rounded-8 bg-card p-3">{children}</section>
}

function SummarySection({ summary }: { summary: Overview['summary'] }): ReactElement {
  return (
    <dl className="grid grid-cols-2 gap-2">
      <div className="col-span-2 flex flex-col gap-1 rounded-8 bg-card p-3">
        <dt className="text-dns-14N-130 text-muted-foreground">総ボリューム</dt>
        <dd className="flex flex-wrap items-baseline gap-3">
          <span className="text-std-32B-150">{formatKg(summary.total_volume)}</span>
          {summary.change_rate !== null && (
            <span className="text-dns-14B-130">前の期間より {formatChangeRate(summary.change_rate)}</span>
          )}
        </dd>
      </div>
      <div className="flex flex-col gap-1 rounded-8 bg-card p-3">
        <dt className="text-dns-14N-130 text-muted-foreground">トレーニング日数</dt>
        <dd className="text-std-20B-150">{summary.training_days} 日</dd>
      </div>
      <div className="flex flex-col gap-1 rounded-8 bg-card p-3">
        <dt className="text-dns-14N-130 text-muted-foreground">総セット数</dt>
        <dd className="flex flex-col text-std-20B-150">
          {summary.set_count} セット
          <span className="text-dns-14N-130 text-muted-foreground">1回あたり {formatKg(summary.volume_per_training_day)}</span>
        </dd>
      </div>
    </dl>
  )
}

function toVolumeRecord(volumes: BodyPartVolume[]): Record<BodyPart, number> {
  const record: Record<BodyPart, number> = { chest: 0, back: 0, shoulders: 0, arms: 0, legs: 0, abs: 0 }
  for (const volume of volumes) record[volume.body_part] = volume.volume
  return record
}

function toBodyPartBars(buckets: VolumeBucket[], unit: BucketUnit): VolumeBars {
  return {
    kind: 'body_part',
    bars: buckets.map((bucket) => ({
      key: bucket.start,
      label: formatBucketLabel(bucket.start, unit),
      volumes: toVolumeRecord(bucket.volumes),
    })),
  }
}

function VolumeTrendSection({ overview }: { overview: Overview }): ReactElement {
  const [unit, setUnit] = useState<BucketUnit>('month')
  const buckets = unit === 'week' ? overview.weekly_volumes : overview.monthly_volumes

  return (
    <Card>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-std-18B-160">総ボリュームの推移</h2>
        <BucketUnitToggle unit={unit} onChange={setUnit} />
      </div>
      <StackedBarChart label={`${BUCKET_UNIT_LABEL[unit]}ごとの総ボリューム`} data={toBodyPartBars(buckets, unit)} />
    </Card>
  )
}

function BodyPartShareSection({ shares }: { shares: Overview['body_part_shares'] }): ReactElement {
  const maxVolume = Math.max(0, ...shares.map((share) => share.volume))
  return (
    <Card>
      <h2 className="text-std-18B-160">部位ごとの総ボリューム</h2>
      <ul className="flex flex-col gap-2">
        {shares.map((share) => (
          <li key={share.body_part} className="flex items-center gap-2 text-dns-14N-130">
            <span className="w-10 shrink-0">{BODY_PART_LABEL[share.body_part]}</span>
            <span className="h-3 flex-1 rounded-4 bg-background">
              <span
                className="block h-full rounded-4 bg-primary"
                style={{ width: `${maxVolume > 0 ? (share.volume / maxVolume) * 100 : 0}%` }}
              />
            </span>
            <span className="w-32 shrink-0 text-right">
              {formatKg(share.volume)} {Math.round(share.share * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function AnnualVolumeSection({ annual }: { annual: Overview['annual'] }): ReactElement {
  const thisYearTotal = annual.this_year.at(-1)?.cumulative_volume ?? 0
  const toPoints = (months: Overview['annual']['this_year']) =>
    months.map((month) => ({ x: month.month, y: month.cumulative_volume }))

  return (
    <Card>
      <h2 className="text-std-18B-160">年間の総ボリューム</h2>
      <p className="text-dns-14N-130 text-muted-foreground">期間の指定によらず、1月1日からの累計を表示します</p>
      <div className="flex flex-wrap items-baseline gap-3">
        <span className="text-std-32B-150">{formatKg(thisYearTotal)}</span>
        {annual.change_rate !== null && (
          <span className="text-dns-14B-130">{annual.year - 1}年の同じ時期より {formatChangeRate(annual.change_rate)}</span>
        )}
      </div>
      <LineChart
        label={`${annual.year}年と${annual.year - 1}年の総ボリュームの累計`}
        series={[
          { key: 'last-year', label: `${annual.year - 1}年`, variant: 'dashed_gray', points: toPoints(annual.last_year) },
          { key: 'this-year', label: `${annual.year}年`, variant: 'solid', points: toPoints(annual.this_year) },
        ]}
        yAxis="zero"
        formatX={(month) => `${month}月`}
        formatY={formatAxisValue}
      />
      <dl className="flex justify-between border-t border-border pt-2 text-dns-14N-130">
        <dt className="text-muted-foreground">{annual.year - 1}年の合計</dt>
        <dd className="font-bold">{formatKg(annual.last_year_total_volume)}</dd>
      </dl>
    </Card>
  )
}

function Big3Section({ big3 }: { big3: Overview['big3'] }): ReactElement {
  const remaining = big3.goal - big3.total
  return (
    <Card>
      <div className="flex items-baseline justify-between">
        <h2 className="text-std-18B-160">BIG3 合計</h2>
        <span className="text-dns-14N-130 text-muted-foreground">目標 {formatKg(big3.goal)}</span>
      </div>
      <div className="flex items-baseline gap-3">
        <span className="text-std-32B-150">{formatKg(big3.total)}</span>
        <span className="text-std-16B-170 text-primary">{remaining > 0 ? `あと ${formatKg(remaining)}` : '目標に届いています'}</span>
      </div>
      <div
        role="progressbar"
        aria-label="BIG3 合計"
        aria-valuemin={0}
        aria-valuemax={big3.goal}
        aria-valuenow={big3.total}
        className="h-3 overflow-hidden rounded-full bg-background"
      >
        <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(big3.total / big3.goal, 1) * 100}%` }} />
      </div>
      <dl className="grid grid-cols-3 gap-2">
        {big3.lifts.map((lift) => (
          <div key={lift.exercise_name} className="flex flex-col gap-0.5">
            <dt className="text-dns-14N-130 text-muted-foreground">{lift.exercise_name}</dt>
            <dd className="text-std-16B-170">{lift.e1rm === null ? '-' : formatKg(lift.e1rm)}</dd>
          </div>
        ))}
      </dl>
      <p className="text-dns-14N-130 text-muted-foreground">期間内の推定1RM の最大値を合計しています</p>
    </Card>
  )
}

function OverviewTab({ fromDate, toDate }: { fromDate: string; toDate: string }): ReactElement {
  const [overview] = useLoadable(
    () => analyticsApi.overview({ from_date: fromDate, to_date: toDate }),
    [fromDate, toDate],
    OVERVIEW_FAILURE_MESSAGE,
  )

  if (overview.status === 'loading') return <Skeleton className="h-96" />
  if (overview.status === 'failed') return <p className="text-muted-foreground">{OVERVIEW_FAILURE_MESSAGE}</p>
  return (
    <>
      <SummarySection summary={overview.value.summary} />
      <VolumeTrendSection overview={overview.value} />
      <BodyPartShareSection shares={overview.value.body_part_shares} />
      <AnnualVolumeSection annual={overview.value.annual} />
      <Big3Section big3={overview.value.big3} />
    </>
  )
}

function toExerciseBars(buckets: ExerciseVolumeBucket[], unit: BucketUnit): VolumeBars {
  return {
    kind: 'total',
    bars: buckets.map((bucket) => ({ key: bucket.start, label: formatBucketLabel(bucket.start, unit), volume: bucket.volume })),
  }
}

function ExerciseAnalyticsView({ uid, fromDate, toDate }: { uid: string; fromDate: string; toDate: string }): ReactElement {
  const [unit, setUnit] = useState<BucketUnit>('month')
  const [analytics] = useLoadable(
    () => analyticsApi.exercise(uid, { from_date: fromDate, to_date: toDate }),
    [uid, fromDate, toDate],
    EXERCISE_FAILURE_MESSAGE,
  )

  if (analytics.status === 'loading') return <Skeleton className="h-96" />
  if (analytics.status === 'failed') return <p className="text-muted-foreground">{EXERCISE_FAILURE_MESSAGE}</p>

  const value = analytics.value
  const trainingMaxPoints = toStepPoints(
    value.training_max_points.map((point) => ({ x: toEpochDay(point.effective_on), y: point.value })),
    { endX: toEpochDay(toDate) },
  )

  return (
    <>
      <dl className="grid grid-cols-3 gap-2">
        {[
          { label: '最大重量', value: value.max_weight },
          { label: '推定1RM の最大', value: value.max_e1rm },
          { label: '総ボリューム', value: value.total_volume },
        ].map((metric) => (
          <div key={metric.label} className="flex flex-col gap-1 rounded-8 bg-card p-3">
            <dt className="text-dns-14N-130 text-muted-foreground">{metric.label}</dt>
            <dd className="text-std-20B-150">{metric.value === null ? '-' : formatKg(metric.value)}</dd>
          </div>
        ))}
      </dl>
      <Card>
        <h2 className="text-std-18B-160">推定1RM の推移</h2>
        <LineChart
          label={`${value.exercise_name}の推定1RM とトレーニングマックスの推移`}
          series={[
            { key: 'training-max', label: 'トレーニングマックス', variant: 'dashed_orange', points: trainingMaxPoints },
            {
              key: 'e1rm',
              label: 'トップセットの推定1RM',
              variant: 'solid',
              points: value.e1rm_points.map((point) => ({ x: toEpochDay(point.date), y: point.e1rm })),
            },
          ]}
          yAxis="fit"
          formatX={formatEpochDay}
          formatY={String}
        />
      </Card>
      <Card>
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-std-18B-160">総ボリューム</h2>
          <BucketUnitToggle unit={unit} onChange={setUnit} />
        </div>
        <StackedBarChart
          label={`${value.exercise_name}の${BUCKET_UNIT_LABEL[unit]}ごとの総ボリューム`}
          data={toExerciseBars(unit === 'week' ? value.weekly_volumes : value.monthly_volumes, unit)}
        />
      </Card>
    </>
  )
}

function ExerciseTab({ fromDate, toDate, periodField }: { fromDate: string; toDate: string; periodField: ReactElement }): ReactElement {
  const [exercises] = useLoadable(() => exercisesApi.list(), [], EXERCISES_FAILURE_MESSAGE)
  const [selectedUid, setSelectedUid] = useState<string | null>(null)

  if (exercises.status === 'loading') return <Skeleton className="h-96" />
  if (exercises.status === 'failed') return <p className="text-muted-foreground">{EXERCISES_FAILURE_MESSAGE}</p>
  if (exercises.value.length === 0) return <p className="text-muted-foreground">種目がありません</p>

  const uid = selectedUid ?? exercises.value[0].uid
  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        {periodField}
        <InputField label="種目">
          <Select value={uid} onChange={(event) => setSelectedUid(event.target.value)}>
            {exercises.value.map((exercise) => (
              <option key={exercise.uid} value={exercise.uid}>
                {exercise.name}
              </option>
            ))}
          </Select>
        </InputField>
      </div>
      <ExerciseAnalyticsView uid={uid} fromDate={fromDate} toDate={toDate} />
    </>
  )
}

export function AnalyticsPage(): ReactElement {
  const [searchParams, setSearchParams] = useSearchParams()
  const today = useToday()
  const [preset, setPreset] = useState<PeriodPreset>('six_months')
  const tab: AnalyticsTab = searchParams.get('tab') === 'exercise' ? 'exercise' : 'overview'
  const fromDate = calculatePeriodStart(preset, today)
  const periodField = <PeriodField preset={preset} onChange={setPreset} />

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-std-24B-150">分析</h1>
      <Tab className="dark:text-solid-gray-50">
        <TabList aria-label="分析の対象">
          {(['overview', 'exercise'] as const).map((candidate) => (
            <TabItem
              key={candidate}
              href={candidate === 'exercise' ? '?tab=exercise' : '?'}
              aria-current={tab === candidate ? 'page' : undefined}
              className="dark:bg-solid-gray-800"
              onClick={(event) => {
                event.preventDefault()
                setSearchParams(candidate === 'exercise' ? { tab: 'exercise' } : {})
              }}
            >
              {candidate === 'overview' ? '全体' : '種目'}
            </TabItem>
          ))}
        </TabList>
      </Tab>
      {tab === 'overview' ? (
        <>
          {periodField}
          <OverviewTab fromDate={fromDate} toDate={today} />
        </>
      ) : (
        <ExerciseTab fromDate={fromDate} toDate={today} periodField={periodField} />
      )}
    </div>
  )
}
