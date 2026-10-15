import type { ReactElement } from 'react'
import { calculateLineAxes, type ChartPoint, type YAxisMode } from '@/lib/analytics'

type LineVariant = 'solid' | 'dashed_gray' | 'dashed_orange'
export type LineSeries = { key: string; label: string; variant: LineVariant; points: ChartPoint[] }

const WIDTH = 334
const HEIGHT = 200
const PLOT_LEFT = 44
const PLOT_RIGHT = 326
const PLOT_TOP = 16
const PLOT_BOTTOM = 176

type LineChartProps = {
  label: string
  series: LineSeries[]
  yAxis: YAxisMode
  formatX: (x: number) => string
  formatY: (y: number) => string
}

function SeriesPath({ variant, points }: { variant: LineVariant; points: string }): ReactElement {
  switch (variant) {
    case 'solid':
      return <polyline points={points} fill="none" strokeWidth={2} className="stroke-primary" />
    case 'dashed_gray':
      return <polyline points={points} fill="none" strokeWidth={2} strokeDasharray="4 3" className="stroke-solid-gray-536" />
    case 'dashed_orange':
      return <polyline points={points} fill="none" strokeWidth={3} strokeDasharray="5 3" className="stroke-warning-orange-2" />
  }
}

function LegendSample({ variant }: { variant: LineVariant }): ReactElement {
  return (
    <svg aria-hidden width={20} height={10} className="shrink-0">
      <SeriesPath variant={variant} points="0,5 20,5" />
    </svg>
  )
}

export function LineChart({ label, series, yAxis, formatX, formatY }: LineChartProps): ReactElement {
  const axes = calculateLineAxes(
    series.flatMap((line) => line.points),
    { yAxis },
  )
  if (axes === null) return <p className="text-muted-foreground">期間内の記録がありません</p>

  const { xRange, yRange, xTicks } = axes
  const toPlotX = (x: number): number => PLOT_LEFT + ((x - xRange.min) / (xRange.max - xRange.min)) * (PLOT_RIGHT - PLOT_LEFT)
  const toPlotY = (y: number): number => PLOT_BOTTOM - ((y - yRange.min) / (yRange.max - yRange.min)) * (PLOT_BOTTOM - PLOT_TOP)
  const yMiddle = (yRange.min + yRange.max) / 2

  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-dns-14N-130">
        {series.map((line) => (
          <li key={line.key} className="flex items-center gap-1.5">
            <LegendSample variant={line.variant} />
            {line.label}
          </li>
        ))}
      </ul>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label} className="h-auto w-full">
        <g className="stroke-solid-gray-100">
          <line x1={PLOT_LEFT} y1={toPlotY(yRange.max)} x2={PLOT_RIGHT} y2={toPlotY(yRange.max)} />
          <line x1={PLOT_LEFT} y1={toPlotY(yMiddle)} x2={PLOT_RIGHT} y2={toPlotY(yMiddle)} />
        </g>
        <line x1={PLOT_LEFT} y1={PLOT_BOTTOM} x2={PLOT_RIGHT} y2={PLOT_BOTTOM} className="stroke-solid-gray-420" />
        <g className="fill-muted-foreground text-dns-14N-130" textAnchor="end">
          {[yRange.max, yMiddle, yRange.min].map((y) => (
            <text key={y} x={PLOT_LEFT - 6} y={toPlotY(y) + 5}>
              {formatY(y)}
            </text>
          ))}
        </g>
        <g className="fill-muted-foreground text-dns-14N-130" textAnchor="middle">
          {xTicks.map((x) => (
            <text key={x} x={toPlotX(x)} y={HEIGHT - 4}>
              {formatX(x)}
            </text>
          ))}
        </g>
        {series.map((line) => (
          <g key={line.key}>
            <SeriesPath variant={line.variant} points={line.points.map((point) => `${toPlotX(point.x)},${toPlotY(point.y)}`).join(' ')} />
            {line.variant === 'solid' &&
              line.points.map((point) => <circle key={point.x} cx={toPlotX(point.x)} cy={toPlotY(point.y)} r={4} className="fill-primary" />)}
          </g>
        ))}
      </svg>
    </div>
  )
}
