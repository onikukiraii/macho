import type { ExerciseHistoryEntry } from '@/api/constants'

export function formatSet(set: ExerciseHistoryEntry['sets'][number]): string {
  return `${set.weight} kg × ${set.reps}${set.rir === null ? '' : ` RIR ${set.rir}`}`
}
