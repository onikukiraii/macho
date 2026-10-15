import { NavLink, Outlet } from 'react-router-dom'
import { ChartLine, Dumbbell, Download, House, ListChecks } from 'lucide-react'

const TABS = [
  { to: '/', label: 'ホーム', icon: House },
  { to: '/program', label: 'プログラム', icon: ListChecks },
  { to: '/exercises', label: '種目', icon: Dumbbell },
  { to: '/analytics', label: '分析', icon: ChartLine },
  { to: '/export', label: '出力', icon: Download },
]

export function TabLayout() {
  return (
    <div className="flex min-h-dvh flex-col pt-[env(safe-area-inset-top)]">
      <main className="flex-1 pb-[calc(5rem+env(safe-area-inset-bottom))]">
        <Outlet />
      </main>
      <nav aria-label="メニュー" className="fixed inset-x-0 bottom-0 border-t border-border bg-card pb-[env(safe-area-inset-bottom)]">
        <ul className="grid grid-cols-5">
          {TABS.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className="flex min-h-14 flex-col items-center justify-center gap-0.5 text-dns-14N-120 text-muted-foreground aria-[current=page]:text-primary aria-[current=page]:font-bold"
              >
                <Icon aria-hidden className="size-6" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
