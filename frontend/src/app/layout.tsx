import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'

export const metadata: Metadata = {
  title: 'OpsCore — AI-Powered Workforce Platform',
  description:
    'Production-grade multi-tenant backend showcase: RBAC, AI agents with tool calling and RAG, async task processing.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
