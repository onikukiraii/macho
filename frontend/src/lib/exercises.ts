import { BODY_PART_ORDER, type BodyPart, type Exercise } from '@/api/constants'
import type { components } from '@/api/schema'

type Schemas = components['schemas']

export function formatSet(set: Pick<Schemas['SetResponse'], 'weight' | 'reps' | 'rir'>): string {
  return `${set.weight} kg × ${set.reps}${set.rir === null ? '' : ` RIR ${set.rir}`}`
}

/** 予定を「3×5〜8 RPE8 80% / 目標 100 kg」の形にする */
export function formatPlanned(planned: Schemas['PlannedResponse'], targetWeight: number | null): string {
  return [
    `${planned.sets}×${planned.reps}${planned.reps_max === null ? '' : `〜${planned.reps_max}`}`,
    planned.target_rpe === null ? '' : ` RPE${planned.target_rpe}`,
    planned.target_percent === null ? '' : ` ${planned.target_percent}%`,
    targetWeight === null ? '' : ` / 目標 ${targetWeight} kg`,
  ].join('')
}

/** 部位の並び順で、種目が1つ以上ある部位だけを返す */
export function groupExercisesByBodyPart(exercises: Exercise[]): { bodyPart: BodyPart; exercises: Exercise[] }[] {
  return BODY_PART_ORDER.map((bodyPart) => ({
    bodyPart,
    exercises: exercises.filter((exercise) => exercise.body_part === bodyPart),
  })).filter((group) => group.exercises.length > 0)
}
