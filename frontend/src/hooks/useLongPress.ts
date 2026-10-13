import { useEffect, useRef, type MouseEvent } from 'react'

const LONG_PRESS_MILLISECONDS = 500

type LongPressHandlers = {
  onPointerDown: () => void
  onPointerUp: () => void
  onPointerLeave: () => void
  onPointerCancel: () => void
  onContextMenu: (event: MouseEvent) => void
}

/** 長押しが成立した時点の `onLongPress` を呼ぶ。押している間に変わった値を使うため */
export function useLongPress(onLongPress: () => void): LongPressHandlers {
  const timeoutId = useRef<ReturnType<typeof setTimeout> | null>(null)
  const latestOnLongPress = useRef(onLongPress)

  useEffect(() => {
    latestOnLongPress.current = onLongPress
  })

  useEffect(() => {
    const pendingTimeoutId = timeoutId
    return () => {
      if (pendingTimeoutId.current !== null) clearTimeout(pendingTimeoutId.current)
    }
  }, [])

  function cancelLongPress(): void {
    if (timeoutId.current !== null) clearTimeout(timeoutId.current)
    timeoutId.current = null
  }

  return {
    onPointerDown: () => {
      cancelLongPress()
      timeoutId.current = setTimeout(() => {
        timeoutId.current = null
        latestOnLongPress.current()
      }, LONG_PRESS_MILLISECONDS)
    },
    onPointerUp: cancelLongPress,
    onPointerLeave: cancelLongPress,
    onPointerCancel: cancelLongPress,
    // iOS で長押ししたときに表示されるメニューを抑止する
    onContextMenu: (event) => event.preventDefault(),
  }
}
