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
    keyframes: {
      swing: {
        '0%': { transform: 'rotate(0deg)' },
        '10%': { transform: 'rotate(15deg)' },   // Quick initial swing to one side
        '20%': { transform: 'rotate(-15deg)' },  // Quick swing to the opposite side
        '30%': { transform: 'rotate(12deg)' },   // Start of noticeable deceleration
        '40%': { transform: 'rotate(-12deg)' },
        '50%': { transform: 'rotate(9deg)' },
        '60%': { transform: 'rotate(-9deg)' },
        '70%': { transform: 'rotate(6deg)' },
        '75%': { transform: 'rotate(-6deg)' },
        '80%': { transform: 'rotate(3deg)' },
        '85%': { transform: 'rotate(-3deg)' },
        '90%': { transform: 'rotate(1.5deg)' },
        '92%': { transform: 'rotate(-1.5deg)' },
        '94%': { transform: 'rotate(0.75deg)' },
        '96%': { transform: 'rotate(-0.75deg)' },
        '98%': { transform: 'rotate(0.375deg)' },
        '100%': { transform: 'rotate(0deg)' }    // Final settle at center
      }
    },
    animation: {
      swing: 'swing 1s ease-out 1', // Use 'ease-out' to emphasize the deceleration at the end
    }
  },
  plugins: [
    require('tailwind-scrollbar')({ nocompatible: true }),
  ],
}

