import type { ReactElement } from 'react'
import type { BodyPart } from '@/api/constants'

export function BodyPartDot({ bodyPart }: { bodyPart: BodyPart }): ReactElement {
  switch (bodyPart) {
    case 'chest':
      return <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-red-600" />
    case 'back':
      return <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-blue-600" />
    case 'shoulders':
      return <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-yellow-600" />
    case 'arms':
      return <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-purple-600" />
    case 'legs':
      return <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-green-600" />
    case 'abs':
      return <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-cyan-600" />
  }
}
