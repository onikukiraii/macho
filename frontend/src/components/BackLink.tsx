import type { MouseEvent, ReactElement, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'

type BackLinkProps = {
  to: string
  children: ReactNode
  onClick?: (event: MouseEvent<HTMLAnchorElement>) => void
}

export function BackLink({ to, children, onClick }: BackLinkProps): ReactElement {
  return (
    <Link to={to} onClick={onClick} className="flex min-h-11 w-fit items-center gap-1 pr-2 text-std-16N-170 text-primary">
      <ChevronLeft aria-hidden className="size-6" />
      {children}
    </Link>
  )
}
