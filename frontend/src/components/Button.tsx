import type { ReactElement } from 'react'
import { Button as DadsButton, type ButtonProps } from '@/components/dads/Button'
import { cn } from '@/lib/utils'

// DADS の Button は色を key-900 に固定しており、ダークモードで --primary の配色へ切り替わらない
export function Button(props: ButtonProps): ReactElement {
  return (
    <DadsButton
      {...props}
      className={cn(
        props.variant === 'solid-fill' &&
          'dark:bg-key-300 dark:text-solid-gray-900 dark:active:bg-key-400 dark:aria-disabled:bg-solid-gray-600 dark:aria-disabled:text-solid-gray-300',
        props.variant === 'outline' && 'dark:bg-transparent dark:text-key-300 dark:active:bg-solid-gray-700',
        props.className,
      )}
    />
  )
}
