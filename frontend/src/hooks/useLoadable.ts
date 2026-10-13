import { useEffect, useState } from 'react'
import { toast } from 'sonner'

export type Loadable<T> = { status: 'loading' } | { status: 'failed' } | { status: 'loaded'; value: T }

type Settled<T> = { load: () => Promise<T>; loadable: Loadable<T> }

/** `load` は useCallback で包んで渡す。`load` が変わると読み込み直す。 */
export function useLoadable<T>(
  load: () => Promise<T>,
  failureMessage: string,
): [Loadable<T>, (value: T) => void] {
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    let cancelled = false
    load()
      .then((value) => !cancelled && setSettled({ load, loadable: { status: 'loaded', value } }))
      .catch(() => {
        if (cancelled) return
        toast.error(failureMessage)
        setSettled({ load, loadable: { status: 'failed' } })
      })
    return () => {
      cancelled = true
    }
  }, [load, failureMessage])

  const loadable: Loadable<T> = settled?.load === load ? settled.loadable : { status: 'loading' }
  return [loadable, (value) => setSettled({ load, loadable: { status: 'loaded', value } })]
}
