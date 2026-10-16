import type { ReactElement } from 'react'
import { BODY_PART_LABEL, BODY_PART_ORDER, type BodyPart } from '@/api/constants'
import { BodyPartDot } from '@/components/BodyPartDot'
import { calculateNiceMax, formatAxisValue, scaleToHeight } from '@/lib/analytics'

type BodyPartBar = { key: string; label: string; volumes: Record<BodyPart, number> }
type TotalBar = { key: string; label: string; volume: number }
export type VolumeBars = { kind: 'body_part'; bars: BodyPartBar[] } | { kind: 'total'; bars: TotalBar[] }

const WIDTH = 334
const HEIGHT = 164
const PLOT_LEFT = 44
const PLOT_RIGHT = 326
const PLOT_TOP = 16
const PLOT_BOTTOM = 136
const PLOT_HEIGHT = PLOT_BOTTOM - PLOT_TOP
const MAX_BAR_WIDTH = 30
const MAX_LABEL_COUNT = 6

type RectProps = { x: number; y: number; width: number; height: number }

function BodyPartRect({ bodyPart, ...rect }: RectProps & { bodyPart: BodyPart }): ReactElement {
  switch (bodyPart) {
    case 'chest':
      return <rect {...rect} className="fill-red-600" />
    case 'back':
      return <rect {...rect} className="fill-blue-600" />
    case 'shoulders':
      return <rect {...rect} className="fill-yellow-600" />
    case 'arms':
      return <rect {...rect} className="fill-purple-600" />
    case 'legs':
      return <rect {...rect} className="fill-green-600" />
    case 'abs':
      return <rect {...rect} className="fill-cyan-600" />
  }
}

function BodyPartStack({ bar, x, width, max }: { bar: BodyPartBar; x: number; width: number; max: number }): ReactElement {
  const heights = BODY_PART_ORDER.map((bodyPart) => scaleToHeight(bar.volumes[bodyPart], { max, height: PLOT_HEIGHT }))
  return (
    <>
      {BODY_PART_ORDER.map((bodyPart, index) => {
        const stackedBelow = heights.slice(0, index).reduce((sum, height) => sum + height, 0)
        const y = PLOT_BOTTOM - stackedBelow - heights[index]
        return <BodyPartRect key={bodyPart} bodyPart={bodyPart} x={x} y={y} width={width} height={heights[index]} />
      })}
    </>
  )
}

function sumBodyPartVolumes(bar: BodyPartBar): number {
  return BODY_PART_ORDER.reduce((sum, bodyPart) => sum + bar.volumes[bodyPart], 0)
}

export function StackedBarChart({ label, data }: { label: string; data: VolumeBars }): ReactElement {
  const totals = data.kind === 'body_part' ? data.bars.map(sumBodyPartVolumes) : data.bars.map((bar) => bar.volume)
  const max = calculateNiceMax(Math.max(0, ...totals))
  const slotWidth = (PLOT_RIGHT - PLOT_LEFT) / Math.max(data.bars.length, 1)
  const barWidth = Math.min(MAX_BAR_WIDTH, slotWidth * 0.7)
  const labelEvery = Math.ceil(data.bars.length / MAX_LABEL_COUNT)
  const barX = (index: number): number => PLOT_LEFT + slotWidth * index + (slotWidth - barWidth) / 2

  return (
    <div className="flex flex-col gap-2">
      {data.kind === 'body_part' && (
        <ul aria-label="部位の凡例" className="flex flex-wrap gap-x-3 gap-y-1 text-dns-14N-130">
          {BODY_PART_ORDER.map((bodyPart) => (
            <li key={bodyPart} className="flex items-center gap-1">
              <BodyPartDot bodyPart={bodyPart} />
              {BODY_PART_LABEL[bodyPart]}
            </li>
          ))}
        </ul>
      )}
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label} className="h-auto w-full">
        <g className="stroke-solid-gray-100 dark:stroke-solid-gray-700">
          <line x1={PLOT_LEFT} y1={PLOT_TOP} x2={PLOT_RIGHT} y2={PLOT_TOP} />
          <line x1={PLOT_LEFT} y1={PLOT_TOP + PLOT_HEIGHT / 2} x2={PLOT_RIGHT} y2={PLOT_TOP + PLOT_HEIGHT / 2} />
        </g>
        <line x1={PLOT_LEFT} y1={PLOT_BOTTOM} x2={PLOT_RIGHT} y2={PLOT_BOTTOM} className="stroke-solid-gray-420" />
        <g className="fill-muted-foreground text-dns-14N-130" textAnchor="end">
          {[max, max / 2, 0].map((value) => (
            <text key={value} x={PLOT_LEFT - 6} y={PLOT_BOTTOM - scaleToHeight(value, { max, height: PLOT_HEIGHT }) + 5}>
              {formatAxisValue(value)}
            </text>
          ))}
        </g>
        {data.kind === 'body_part'
          ? data.bars.map((bar, index) => <BodyPartStack key={bar.key} bar={bar} x={barX(index)} width={barWidth} max={max} />)
          : data.bars.map((bar, index) => {
              const height = scaleToHeight(bar.volume, { max, height: PLOT_HEIGHT })
              return <rect key={bar.key} x={barX(index)} y={PLOT_BOTTOM - height} width={barWidth} height={height} className="fill-primary" />
            })}
        <g className="fill-muted-foreground text-dns-14N-130" textAnchor="middle">
          {data.bars.map(
            (bar, index) =>
              index % labelEvery === 0 && (
                <text key={bar.key} x={barX(index) + barWidth / 2} y={HEIGHT - 8}>
                  {bar.label}
                </text>
              ),
          )}
        </g>
      </svg>
    </div>
  )
}
