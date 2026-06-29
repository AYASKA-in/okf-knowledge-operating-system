import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react"
import { api, API_BASE, setTokens, clearTokens, loadTokens, getAccessToken } from "@/lib/api"
import type { User, Workspace, AuthResponse } from "@/types"

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  activeWorkspaceId: string | null
  setActiveWorkspaceId: (id: string) => void
  workspaces: Workspace[]
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])

  useEffect(() => {
    loadTokens()
    if (getAccessToken()) {
      api.get<User>("/v1/auth/me")
        .then(u => {
          setUser(u)
          setActiveWorkspaceId(u.workspace_id ?? null)
          return u
        })
        .catch(() => clearTokens())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  // Fetch workspaces for admin users
  useEffect(() => {
    if (user?.role === "admin") {
      api.get<Workspace[]>("/v1/admin/workspaces")
        .then(setWorkspaces)
        .catch(() => {})
    }
  }, [user?.role])

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<AuthResponse>("/v1/auth/token", { email, password })
    setTokens(data.access_token, data.refresh_token)
    const me = await api.get<User>("/v1/auth/me")
    setUser(me)
    setActiveWorkspaceId(me.workspace_id ?? data.workspace_id ?? null)
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
    setActiveWorkspaceId(null)
    setWorkspaces([])
  }, [])

  const handleSetWorkspace = useCallback((id: string) => {
    setActiveWorkspaceId(id)
  }, [])

  const isAdmin = user?.role === "admin"

  return (
    <AuthContext.Provider value={{
      user, loading, login, logout,
      isAuthenticated: !!user,
      activeWorkspaceId,
      setActiveWorkspaceId: handleSetWorkspace,
      workspaces,
      isAdmin,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
