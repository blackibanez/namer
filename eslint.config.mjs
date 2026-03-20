import globals from 'globals'
import pluginJs from '@eslint/js'

export default [
  { languageOptions: { globals: globals.browser } },
  {
    files: ['webpack.prod.js'],
    languageOptions: {
      globals: globals.node,
    },
  },
  pluginJs.configs.recommended,
]
