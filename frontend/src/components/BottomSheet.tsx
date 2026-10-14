import type { ReactElement, ReactNode } from 'react'
import { X } from 'lucide-react'
import { useModalDialog } from '@/components/dads/ModalDialog'

type BottomSheetProps = {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}

export function BottomSheet({ open, onClose, title, children }: BottomSheetProps): ReactElement {
  const { dialogProps, headingProps, closeButtonProps } = useModalDialog({ open, onOpenChange: onClose })

  return (
    <dialog
      {...dialogProps}
      className="mx-0 mb-0 mt-auto max-h-[85dvh] w-full max-w-none rounded-t-16 bg-card p-0 text-card-foreground backdrop:bg-black/60"
    >
      <div className="flex flex-col gap-4 p-4 pb-[max(2rem,calc(1rem+env(safe-area-inset-bottom)))]">
        <div className="flex items-center gap-4">
          <h2 {...headingProps} tabIndex={-1} className="grow text-std-20B-150 focus-visible:outline-none">
            {title}
          </h2>
          <button
            type="button"
            {...closeButtonProps}
            className="flex min-h-11 shrink-0 items-center gap-1 rounded-6 px-3 text-oln-16N-100 text-foreground hover:bg-secondary"
          >
            <X aria-hidden className="size-6" />
            閉じる
          </button>
        </div>
        {open && children}
      </div>
    </dialog>
  )
}
