/** 同じ origin のパスだけを返す。外部への遷移になる値は null にする。 */
export function resolveReturnTo(value: string, origin: string, params: Record<string, string> = {}): string | null {
  if (!URL.canParse(value, origin)) return null
  const url = new URL(value, origin)
  if (url.origin !== origin) return null
  Object.entries(params).forEach(([key, paramValue]) => url.searchParams.set(key, paramValue))
  return url.pathname + url.search + url.hash
}
