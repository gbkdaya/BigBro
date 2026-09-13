import './globals.css'

export const metadata = {
  title: 'App',
  description: 'Scaffolded by BigBro',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
