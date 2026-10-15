/** 作成画面とプレビュー画面のあいだで、location.state で渡す貼り付けた JSON */
export type ProgramDraftLocationState = { jsonText: string }

/** location.state は履歴から復元され、型が保証されないため形を確かめてから使う */
export function readDraftJsonText(state: unknown): string | null {
  if (typeof state !== 'object' || state === null || !('jsonText' in state)) return null
  return typeof state.jsonText === 'string' ? state.jsonText : null
}
