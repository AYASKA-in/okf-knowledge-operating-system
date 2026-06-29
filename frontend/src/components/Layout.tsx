import { type ReactNode } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"
import { useTheme } from "@/contexts/ThemeContext"
import { Button } from "@/components/ui/button"
import { Toaster } from "sonner"
import { WorkspaceSwitcher } from "@/components/WorkspaceSwitcher"
import { Sun, Moon, LogOut, ChevronLeft, FileText, Share2, Upload, LayoutDashboard, MessageSquare } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { path: "/", label: "Knowledge", icon: FileText },
  { path: "/graph", label: "Graph", icon: Share2 },
  { path: "/upload", label: "Upload", icon: Upload },
  { path: "/chat", label: "Chat", icon: MessageSquare },
]

interface LayoutProps {
  children: ReactNode
  showBack?: boolean
  onBack?: () => void
  title?: string
}

export function Layout({ children, showBack, onBack, title }: LayoutProps) {
  const { logout, isAdmin } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {showBack && (
              <Button variant="ghost" size="icon" onClick={onBack ?? (() => navigate(-1))}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}
            {title && <h1 className="text-lg font-semibold truncate">{title}</h1>}
          </div>

          <div className="hidden sm:flex items-center gap-1">
            <WorkspaceSwitcher />
            {navItems.map(item => {
              const Icon = item.icon
              return (
                <Button
                  key={item.path}
                  variant={location.pathname === item.path ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => navigate(item.path)}
                >
                  <Icon className="h-4 w-4 mr-1.5" />
                  {item.label}
                </Button>
              )
            })}
            {isAdmin && (
              <Button
                variant={location.pathname.startsWith("/admin") ? "secondary" : "ghost"}
                size="sm"
                onClick={() => navigate("/admin")}
              >
                <LayoutDashboard className="h-4 w-4 mr-1.5" />
                Admin
              </Button>
            )}
          </div>

          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={toggle} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={logout} title="Logout">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {/* Mobile nav */}
        <div className="sm:hidden border-t flex">
          {navItems.map(item => {
            const Icon = item.icon
            return (
              <Button
                key={item.path}
                variant="ghost"
                size="sm"
                className={cn(
                  "flex-1 rounded-none h-10",
                  location.pathname === item.path && "bg-muted"
                )}
                onClick={() => navigate(item.path)}
              >
                <Icon className="h-4 w-4" />
              </Button>
            )
          })}
          {isAdmin && (
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "flex-1 rounded-none h-10",
                location.pathname.startsWith("/admin") && "bg-muted"
              )}
              onClick={() => navigate("/admin")}
            >
              <LayoutDashboard className="h-4 w-4" />
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {children}
      </main>

      <Toaster richColors position="top-right" />
    </div>
  )
}
