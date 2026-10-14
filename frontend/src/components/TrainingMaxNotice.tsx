import type { ReactElement } from 'react'
import type { components } from '@/api/schema'

type TrainingMaxNoticeProps = {
  trainingMaxUpdates: components['schemas']['TrainingMaxUpdateResponse'][]
}

export function TrainingMaxNotice({ trainingMaxUpdates }: TrainingMaxNoticeProps): ReactElement {
  return (
    <div role="status" className="flex flex-col gap-1 rounded-8 bg-success-2 p-3 text-white">
      <p className="text-std-16B-170">トレーニングマックスを更新しました</p>
      <ul className="text-dns-14N-130">
        {trainingMaxUpdates.map((update) => (
          <li key={update.exercise_name}>
            {update.exercise_name} {update.before.toFixed(1)} → {update.after.toFixed(1)}
          </li>
        ))}
      </ul>
    </div>
  )
}
