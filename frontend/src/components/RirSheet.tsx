import { useState, type ReactElement } from 'react'
import { BottomSheet } from '@/components/BottomSheet'
import { Button } from '@/components/Button'
import { evaluateRirAnswers } from '@/lib/rir'

type RirSheetProps = {
  open: boolean
  onClose: () => void
  onDecide: (rir: number) => void
}

function RirQuestions({ onClose, onDecide }: Omit<RirSheetProps, 'open'>): ReactElement {
  const [answers, setAnswers] = useState<boolean[]>([])
  const evaluation = evaluateRirAnswers(answers)

  if (evaluation.status === 'asking') {
    return (
      <div className="flex flex-col gap-6">
        <p className="text-std-20B-150">あと{evaluation.reps}回、絶対いける？</p>
        <div className="grid grid-cols-2 gap-4">
          <Button size="lg" variant="outline" onClick={() => setAnswers([...answers, false])}>
            いいえ
          </Button>
          <Button size="lg" variant="solid-fill" onClick={() => setAnswers([...answers, true])}>
            はい
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="text-std-20B-150">
        RIR {evaluation.rir}、RPE {evaluation.rpe.toFixed(1)}
      </p>
      <div className="grid grid-cols-2 gap-4">
        <Button size="lg" variant="outline" onClick={() => setAnswers([])}>
          やり直す
        </Button>
        <Button
          size="lg"
          variant="solid-fill"
          onClick={() => {
            onDecide(evaluation.rir)
            onClose()
          }}
        >
          決定
        </Button>
      </div>
    </div>
  )
}

export function RirSheet({ open, onClose, onDecide }: RirSheetProps): ReactElement {
  return (
    <BottomSheet open={open} onClose={onClose} title="RIR">
      <RirQuestions onClose={onClose} onDecide={onDecide} />
    </BottomSheet>
  )
}
