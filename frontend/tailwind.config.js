/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        accent: 'var(--accent)',
        'sev-high': 'var(--sev-high)',
        'sev-high-bg': 'var(--sev-high-bg)',
        'sev-med': 'var(--sev-med)',
        'sev-med-bg': 'var(--sev-med-bg)',
        'sev-low': 'var(--sev-low)',
        'sev-low-bg': 'var(--sev-low-bg)',
        ok: 'var(--ok)',
        'ok-bg': 'var(--ok-bg)',
      },
      fontFamily: {
        mono: 'var(--mono)',
      },
    },
  },
  plugins: [],
}
