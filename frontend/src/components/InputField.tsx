import type { ReactElement, ReactNode } from 'react'
import { Label } from '@/components/dads/Label'

type InputFieldProps = {
  label: string
  children: ReactNode
}

export function InputField({ label, children }: InputFieldProps): ReactElement {
  return (
    <Label size="sm" className="flex flex-col gap-1 dark:text-solid-gray-50 dark:[&_:is(input,textarea,select)]:bg-solid-gray-900 dark:[&_:is(input,textarea,select)]:text-solid-gray-50">
      {label}
      {children}
    </Label>
  )
}
