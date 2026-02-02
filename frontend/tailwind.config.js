/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'var(--primary)',
          hover: 'var(--primary-hover)',
          active: 'var(--primary-active)',
        },
        surface: 'var(--surface)',
        background: 'var(--background)',
        border: 'var(--border)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
      },
      spacing: {
        'sidebar': '250px',
        'knowledge': '300px',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
