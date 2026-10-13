import { useRef, type MouseEvent } from 'react'

const LONG_PRESS_MILLISECONDS = 500

type LongPressHandlers = {
  onPointerDown: () => void
  onPointerUp: () => void
  onPointerLeave: () => void
  onPointerCancel: () => void
  onContextMenu: (event: MouseEvent) => void
}

export function useLongPress(onLongPress: () => void): LongPressHandlers {
  const timeoutId = useRef<ReturnType<typeof setTimeout> | null>(null)

  function cancelLongPress(): void {
    if (timeoutId.current !== null) clearTimeout(timeoutId.current)
    timeoutId.current = null
  }

  return {
    onPointerDown: () => {
      cancelLongPress()
      timeoutId.current = setTimeout(() => {
        timeoutId.current = null
        onLongPress()
      }, LONG_PRESS_MILLISECONDS)
    },
    onPointerUp: cancelLongPress,
    onPointerLeave: cancelLongPress,
    onPointerCancel: cancelLongPress,
    // iOS の長押しで出るメニューを抑える
    onContextMenu: (event) => event.preventDefault(),
  }
}
