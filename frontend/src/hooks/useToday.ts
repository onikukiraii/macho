import { useEffect, useState } from 'react'
import { toDateInputValue } from '@/lib/dates'

/** 端末の今日の日付。開いたまま日をまたいだときのため、画面に戻るたびに取り直す */
export function useToday(): string {
  const [today, setToday] = useState(() => toDateInputValue(new Date()))

  useEffect(() => {
    function refreshToday(): void {
      setToday(toDateInputValue(new Date()))
    }
    function refreshTodayWhenVisible(): void {
      if (document.visibilityState === 'visible') refreshToday()
    }
    window.addEventListener('focus', refreshToday)
    document.addEventListener('visibilitychange', refreshTodayWhenVisible)
    return () => {
      window.removeEventListener('focus', refreshToday)
      document.removeEventListener('visibilitychange', refreshTodayWhenVisible)
    }
  }, [])

  return today
}
