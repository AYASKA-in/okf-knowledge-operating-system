import { useState } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Check, ChevronDown, Building2 } from "lucide-react"
import { cn } from "@/lib/utils"

export function WorkspaceSwitcher() {
  const { workspaces, activeWorkspaceId, setActiveWorkspaceId, isAdmin } = useAuth()
  const [open, setOpen] = useState(false)

  if (!isAdmin || workspaces.length === 0) return null

  const active = workspaces.find(w => w.id === activeWorkspaceId)

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        className="gap-1.5 text-sm"
        onClick={() => setOpen(!open)}
      >
        <Building2 className="h-4 w-4" />
        <span className="max-w-[120px] truncate">{active?.name ?? "Select workspace"}</span>
        <ChevronDown className="h-3 w-3 text-muted-foreground" />
      </Button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute top-full left-0 mt-1 z-50 w-56 rounded-md border bg-popover p-1 shadow-md">
            {workspaces.map(w => (
              <button
                key={w.id}
                className={cn(
                  "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground",
                  w.id === activeWorkspaceId && "bg-accent"
                )}
                onClick={() => { setActiveWorkspaceId(w.id); setOpen(false) }}
              >
                <Building2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="flex-1 text-left truncate">{w.name}</span>
                {w.id === activeWorkspaceId && <Check className="h-3.5 w-3.5" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
