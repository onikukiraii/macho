import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'src/components/ui', 'src/components/dads', 'src/api/schema.d.ts', 'src/test']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      'react-hooks/exhaustive-deps': ['error', { additionalHooks: 'useLoadable' }],
      'no-restricted-imports': ['error', {
        patterns: [{
          regex: '^@/components/ui/(alert|badge|button|checkbox|dialog|input|label|select|separator|sheet|table)$',
          message: 'デジタル庁デザインシステムに同じ部品があります。src/components/dads/ の部品を使ってください。',
        }, {
          regex: '^@/components/dads/Button$',
          message: 'ダークモードの配色を持つ @/components/Button を使ってください。',
        }],
      }],
    },
  },
  {
    files: ['src/components/Button.tsx'],
    rules: { 'no-restricted-imports': 'off' },
  },
])
