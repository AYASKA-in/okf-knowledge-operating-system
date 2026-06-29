import { type ReactNode } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Building2, Users, Cable, ScrollText, ArrowLeft } from "lucide-react"

const adminNavItems = [
  { path: "/admin/workspaces", label: "Workspaces", icon: Building2 },
  { path: "/admin/users", label: "Users", icon: Users },
  { path: "/admin/connectors", label: "Connectors", icon: Cable },
  { path: "/admin/audit", label: "Audit Log", icon: ScrollText },
]

export function AdminLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="flex gap-6">
      <aside className="hidden md:flex flex-col w-56 shrink-0 gap-1">
        <Button variant="ghost" size="sm" className="justify-start mb-2" onClick={() => navigate("/")}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Back to app
        </Button>
        {adminNavItems.map(item => {
          const Icon = item.icon
          return (
            <Button
              key={item.path}
              variant={location.pathname === item.path ? "secondary" : "ghost"}
              className="justify-start"
              onClick={() => navigate(item.path)}
            >
              <Icon className="h-4 w-4 mr-2" /> {item.label}
            </Button>
          )
        })}
      </aside>

      {/* Mobile nav */}
      <div className="md:hidden flex overflow-x-auto gap-1 pb-2 -mx-4 px-4">
        {adminNavItems.map(item => {
          const Icon = item.icon
          return (
            <Button
              key={item.path}
              variant={location.pathname === item.path ? "secondary" : "outline"}
              size="sm"
              className="shrink-0"
              onClick={() => navigate(item.path)}
            >
              <Icon className="h-4 w-4 mr-1.5" /> {item.label}
            </Button>
          )
        })}
      </div>

      <main className={cn("flex-1 min-w-0")}>
        {children}
      </main>
    </div>
  )
}
