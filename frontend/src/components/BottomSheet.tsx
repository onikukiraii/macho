import type { ReactNode } from 'react'
import { ModalDialogClose, useModalDialog } from '@/components/dads/ModalDialog'

type BottomSheetProps = {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}

export function BottomSheet({ open, onClose, title, children }: BottomSheetProps) {
  const { dialogProps, headingProps, closeButtonProps } = useModalDialog({ open, onOpenChange: onClose })

  return (
    <dialog
      {...dialogProps}
      className="m-0 mt-auto max-h-[85dvh] w-full max-w-none rounded-t-16 bg-card p-0 text-card-foreground backdrop:bg-black/60"
    >
      <div className="flex flex-col gap-4 p-4 pb-8">
        <div className="flex items-start gap-4">
          <h2 {...headingProps} tabIndex={-1} className="grow text-std-20B-150 focus-visible:outline-none">
            {title}
          </h2>
          <ModalDialogClose {...closeButtonProps} className="!text-foreground hover:!bg-secondary" />
        </div>
        {children}
      </div>
    </dialog>
  )
}
