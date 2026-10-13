import type { components } from '@/api/schema'

type TrainingMaxUpdate = components['schemas']['TrainingMaxUpdateResponse']

/** 記録の作成から記録の画面へ遷移するときに、location.state で渡す値 */
export type TrainingLogLocationState = { trainingMaxUpdates: TrainingMaxUpdate[] }

function isTrainingMaxUpdate(value: unknown): value is TrainingMaxUpdate {
  return (
    typeof value === 'object' &&
    value !== null &&
    'exercise_name' in value &&
    typeof value.exercise_name === 'string' &&
    'before' in value &&
    typeof value.before === 'number' &&
    'after' in value &&
    typeof value.after === 'number'
  )
}

/** location.state は履歴から復元され、型が保証されないため形を確かめてから使う */
export function readTrainingMaxUpdates(state: unknown): TrainingMaxUpdate[] {
  if (typeof state !== 'object' || state === null || !('trainingMaxUpdates' in state)) return []
  const { trainingMaxUpdates } = state
  return Array.isArray(trainingMaxUpdates) && trainingMaxUpdates.every(isTrainingMaxUpdate) ? trainingMaxUpdates : []
}
