import { useEffect, useState, type DependencyList } from 'react'
import { toast } from 'sonner'

export type Loadable<T> = { status: 'loading' } | { status: 'failed' } | { status: 'loaded'; value: T }

type Settled<T> = { deps: DependencyList; loadable: Loadable<T> }

function isSameDeps(left: DependencyList, right: DependencyList): boolean {
  return left.length === right.length && left.every((value, index) => Object.is(value, right[index]))
}

/** `deps` が変わると読み込み直す。`load` が使う値の `deps` への漏れは eslint の `additionalHooks` で検査する */
export function useLoadable<T>(
  load: () => Promise<T>,
  deps: DependencyList,
  failureMessage: string,
): [Loadable<T>, (value: T) => void] {
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    let cancelled = false
    load()
      .then((value) => !cancelled && setSettled({ deps, loadable: { status: 'loaded', value } }))
      .catch(() => {
        if (cancelled) return
        toast.error(failureMessage)
        setSettled({ deps, loadable: { status: 'failed' } })
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 呼び出し側の deps を additionalHooks で検査している
  }, deps)

  const loadable: Loadable<T> = settled !== null && isSameDeps(settled.deps, deps) ? settled.loadable : { status: 'loading' }
  return [loadable, (value) => setSettled({ deps, loadable: { status: 'loaded', value } })]
}
