/** 同じ origin のパスだけを返す。外部への遷移になる値は null にする。 */
export function resolveReturnTo(value: string, origin: string, params: Record<string, string> = {}): string | null {
  if (!URL.canParse(value, origin)) return null
  const url = new URL(value, origin)
  // `/.//evil.com` は pathname が `//evil.com` になり、遷移先で別の origin と解釈される
  if (url.origin !== origin || url.pathname.startsWith('//')) return null
  Object.entries(params).forEach(([key, paramValue]) => url.searchParams.set(key, paramValue))
  return url.pathname + url.search + url.hash
}
