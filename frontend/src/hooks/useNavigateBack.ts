import type { MouseEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

// ホーム画面から開いたアプリにはブラウザの戻るボタンが無い。履歴があれば1つ前へ戻し、
// URL を直接開いて履歴が無いときはリンク先へ遷移させる
export function useNavigateBack(): (event: MouseEvent<HTMLAnchorElement>) => void {
  const navigate = useNavigate()
  const location = useLocation()

  return function navigateBack(event) {
    if (location.key === 'default') return
    event.preventDefault()
    navigate(-1)
  }
}
