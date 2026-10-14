export function formatRestTime(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

/** 端末の時計での終了時刻から残り秒数を求める。0 から totalSeconds の範囲に収める */
export function remainingRestSeconds(endsAtMs: number, nowMs: number, totalSeconds: number): number {
  return Math.min(totalSeconds, Math.max(0, Math.ceil((endsAtMs - nowMs) / 1000)))
}

export function remainingRestRatio(remainingSeconds: number, totalSeconds: number): number {
  return remainingSeconds / totalSeconds
}
