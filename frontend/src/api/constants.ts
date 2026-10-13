// API スキーマからの型エイリアスとランタイム定数をここに定義する
//
// --- 型エイリアス ---
// API スキーマの型を re-export して、各ページから直接 schema を参照しなくて済むようにする
//
// import type { components } from './schema'
// export type UserResponse = components['schemas']['UserResponse']
// export type UserCreateParams = components['schemas']['UserCreateParams']
//
// --- ランタイム用ラベルマップ ---
// Enum値を日本語ラベルに変換するマップを定義する
//
// import type { components } from './schema'
// export type Status = components['schemas']['Status']
//
// export const STATUS_LABEL: Record<Status, string> = {
//   draft: '下書き',
//   published: '公開中',
//   archived: 'アーカイブ',
// }
