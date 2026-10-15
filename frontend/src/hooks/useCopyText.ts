import { useState } from 'react'
import { toast } from 'sonner'

type CopyMessages = { succeeded: string; failed: string }

/**
 * 取得した文字列をクリップボードへ書く。iPhone の Safari はタップから時間が空いた書き込みを拒むため、
 * 取得の完了を待たずに Promise のまま ClipboardItem へ渡す
 */
export function useCopyText(): { copying: boolean; copyText: (loadText: () => Promise<string>, messages: CopyMessages) => Promise<void> } {
  const [copying, setCopying] = useState(false)

  async function copyText(loadText: () => Promise<string>, messages: CopyMessages): Promise<void> {
    if (copying) return
    setCopying(true)
    try {
      const blob = loadText().then((text) => new Blob([text], { type: 'text/plain' }))
      await navigator.clipboard.write([new ClipboardItem({ 'text/plain': blob })])
      toast.success(messages.succeeded)
    } catch {
      toast.error(messages.failed)
    } finally {
      setCopying(false)
    }
  }

  return { copying, copyText }
}
