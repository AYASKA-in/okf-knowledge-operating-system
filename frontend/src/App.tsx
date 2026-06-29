import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "@/contexts/AuthContext"
import { ThemeProvider } from "@/contexts/ThemeContext"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { AdminLayout } from "@/components/AdminLayout"
import Login from "@/pages/Login"
import KnowledgeList from "@/pages/KnowledgeList"
import ConceptDetail from "@/pages/ConceptDetail"
import GraphView from "@/pages/GraphView"
import UploadDashboard from "@/pages/UploadDashboard"
import WorkspacesPage from "@/pages/admin/WorkspacesPage"
import UsersPage from "@/pages/admin/UsersPage"
import ConnectorsPage from "@/pages/admin/ConnectorsPage"
import AuditLogPage from "@/pages/admin/AuditLogPage"
import ChatPage from "@/pages/ChatPage"
import type { ReactNode } from "react"

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function PublicRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>
  return isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>
}

function AdminGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading, isAdmin } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!isAdmin) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Access denied. Admin only.</div>
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ErrorBoundary>
            <Routes>
              <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
              <Route path="/" element={<ProtectedRoute><KnowledgeList /></ProtectedRoute>} />
              <Route path="/concept/:id" element={<ProtectedRoute><ConceptDetail /></ProtectedRoute>} />
              <Route path="/graph" element={<ProtectedRoute><GraphView /></ProtectedRoute>} />
              <Route path="/upload" element={<ProtectedRoute><UploadDashboard /></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
              <Route path="/admin" element={<AdminGuard><AdminLayout><Navigate to="/admin/workspaces" replace /></AdminLayout></AdminGuard>} />
              <Route path="/admin/workspaces" element={<AdminGuard><AdminLayout><WorkspacesPage /></AdminLayout></AdminGuard>} />
              <Route path="/admin/users" element={<AdminGuard><AdminLayout><UsersPage /></AdminLayout></AdminGuard>} />
              <Route path="/admin/connectors" element={<AdminGuard><AdminLayout><ConnectorsPage /></AdminLayout></AdminGuard>} />
              <Route path="/admin/audit" element={<AdminGuard><AdminLayout><AuditLogPage /></AdminLayout></AdminGuard>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ErrorBoundary>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
