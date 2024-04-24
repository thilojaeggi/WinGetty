/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.j2", "./app/**/*.html"],
  darkMode: 'class',
  theme: {
    extend:
    {
      fontFamily: {
        'poppins': ['Poppins', 'sans-serif']
      },
    },
  },
  plugins: [
    require('tailwind-scrollbar')({ nocompatible: true }),
  ],
}

