import { Timer } from 'lucide-react'

type RestTimerBadgeProps = {
  remainingSeconds: number
  onOpen: () => void
}

export function RestTimerBadge({ remainingSeconds, onOpen }: RestTimerBadgeProps) {
  return (
    <div className="fixed inset-x-0 bottom-0 pb-[env(safe-area-inset-bottom)]">
      <div className="p-4">
        <button
          type="button"
          onClick={onOpen}
          className="flex min-h-14 w-full items-center justify-center gap-2 rounded-16 bg-primary text-std-18B-160 text-primary-foreground tabular-nums shadow-lg"
        >
          <Timer aria-hidden className="size-6" />
          レスト {Math.floor(remainingSeconds / 60)}:{String(remainingSeconds % 60).padStart(2, '0')}
        </button>
      </div>
    </div>
  )
}
