export const RIR_QUESTION_COUNT = 3

export type RirEvaluation = { status: 'asking'; reps: number } | { status: 'answered'; rir: number; rpe: number }

/** 「あと n 回、絶対いける？」に n = 1 から順に答えた回答から、次の質問か RIR と RPE を返す */
export function evaluateRirAnswers(answers: boolean[]): RirEvaluation {
  const rir = answers.indexOf(false)
  if (rir !== -1) return { status: 'answered', rir, rpe: 10 - rir }
  if (answers.length < RIR_QUESTION_COUNT) return { status: 'asking', reps: answers.length + 1 }
  return { status: 'answered', rir: RIR_QUESTION_COUNT, rpe: 10 - RIR_QUESTION_COUNT }
}
