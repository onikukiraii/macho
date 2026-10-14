import { Timer } from 'lucide-react'
import { Button } from '@/components/Button'
import { formatRestTime } from '@/lib/restTimer'

type RestTimerBadgeProps = {
  remainingSeconds: number
  onOpen: () => void
}

export function RestTimerBadge({ remainingSeconds, onOpen }: RestTimerBadgeProps) {
  return (
    <Button size="lg" variant="solid-fill" onClick={onOpen} className="w-full tabular-nums shadow-lg">
      <Timer aria-hidden className="size-6" />
      レスト {formatRestTime(remainingSeconds)}
    </Button>
  )
}
