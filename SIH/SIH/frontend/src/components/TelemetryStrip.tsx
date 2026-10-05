import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  YAxis,
} from 'recharts'
import { formatNumber } from '../format'
import type { TelemetrySample } from '../types'

type Metric = {
  title: string
  detail?: string
  key: 'rop_mph' | 'torque_knm' | 'spp_bar' | 'flow_delta'
  unit: string
  digits: number
  zeroLine?: boolean
}

const metrics: Metric[] = [
  { title: 'ROP', detail: 'Rate of penetration', key: 'rop_mph', unit: 'm/h', digits: 1 },
  { title: 'Torque', key: 'torque_knm', unit: 'kN·m', digits: 1 },
  { title: 'Standpipe pressure', key: 'spp_bar', unit: 'bar', digits: 0 },
  { title: 'Flow balance', detail: 'Flow out minus flow in; negative means returns are short', key: 'flow_delta', unit: 'L/min', digits: 0, zeroLine: true },
]

const trendWindow = 30

export function TelemetryStrip({ history }: { history: TelemetrySample[] }) {
  const data = history.map((sample) => ({
    ...sample,
    flow_delta: sample.flow_out_lpm - sample.flow_in_lpm,
  }))
  const latest = data.at(-1)
  const reference = data.length > trendWindow ? data[data.length - 1 - trendWindow] : data[0]
  const span = latest && data[0] ? latest.timestamp_offset_s - data[0].timestamp_offset_s : 0

  return (
    <section className="panel telemetry-panel" aria-labelledby="telemetry-title">
      <header className="panel-header">
        <div className="panel-title">
          <h2 id="telemetry-title">Drilling parameters</h2>
          <span className="panel-meta">Simulated eRTMAC feed · 1 Hz · last {formatNumber(span + (latest ? 1 : 0))} s</span>
        </div>
      </header>
      <div className="telemetry-grid">
        {metrics.map((metric) => {
          const current = latest?.[metric.key]
          const previous = reference?.[metric.key]
          const delta = typeof current === 'number' && typeof previous === 'number' && data.length > 1 ? current - previous : null
          const roundedDelta = delta === null ? null : Number(delta.toFixed(metric.digits))
          return (
            <article className="metric" key={metric.key} title={metric.detail}>
              <div className="metric-readout">
                <span className="metric-label">{metric.title}</span>
                <span className="metric-value">
                  <strong className="tabular">{typeof current === 'number' ? formatNumber(current, metric.digits) : '—'}</strong>
                  <small>{metric.unit}</small>
                </span>
                <span className="metric-delta tabular">
                  {roundedDelta === null
                    ? 'Waiting for samples'
                    : roundedDelta === 0
                      ? `Steady over ${Math.min(trendWindow, data.length - 1)} s`
                      : `${roundedDelta > 0 ? '+' : '−'}${formatNumber(Math.abs(roundedDelta), metric.digits)} over ${Math.min(trendWindow, data.length - 1)} s`}
                </span>
              </div>
              <div className="metric-chart" aria-hidden="true">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data} margin={{ top: 6, right: 2, bottom: 4, left: 2 }}>
                    <YAxis
                      hide
                      domain={metric.zeroLine
                        ? [(min: number) => Math.min(min, -5) - 2, (max: number) => Math.max(max, 5) + 2]
                        : ['dataMin - 1', 'dataMax + 1']}
                    />
                    {metric.zeroLine && <ReferenceLine y={0} stroke="var(--chart-zero)" strokeDasharray="3 3" />}
                    <Tooltip
                      cursor={{ stroke: 'var(--line-strong)' }}
                      contentStyle={{
                        background: 'var(--bg-2)',
                        border: '1px solid var(--line-strong)',
                        borderRadius: 8,
                        color: 'var(--text-1)',
                        fontSize: 12,
                        padding: '6px 10px',
                      }}
                      labelStyle={{ color: 'var(--text-3)', marginBottom: 2 }}
                      itemStyle={{ color: 'var(--text-1)', padding: 0 }}
                      labelFormatter={(_, payload) => {
                        const offset = payload?.[0]?.payload?.timestamp_offset_s
                        return typeof offset === 'number' ? `T+${offset} s` : ''
                      }}
                      formatter={(value) => [
                        `${typeof value === 'number' ? formatNumber(value, metric.digits) : value} ${metric.unit}`,
                        metric.title,
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey={metric.key}
                      stroke="var(--chart-line)"
                      strokeWidth={1.5}
                      fill="var(--chart-fill)"
                      dot={false}
                      activeDot={{ r: 3, stroke: 'var(--bg-1)', strokeWidth: 2, fill: 'var(--text-1)' }}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
