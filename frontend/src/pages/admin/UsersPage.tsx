import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { useAuth } from "@/contexts/AuthContext"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { Plus, Pencil, Trash2 } from "lucide-react"
import { toast } from "sonner"
import type { User } from "@/types"

export default function UsersPage() {
  const { workspaces } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [role, setRole] = useState("viewer")
  const [workspaceId, setWorkspaceId] = useState("")
  const [saving, setSaving] = useState(false)

  const fetch = () => {
    setLoading(true)
    api.get<{ items: User[]; total?: number }>("/v1/admin/users")
      .then(data => setUsers(data.items || data))
      .catch(() => toast.error("Failed to load users"))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetch() }, [])

  const openCreate = () => {
    setEditing(null); setEmail(""); setPassword(""); setDisplayName(""); setRole("viewer")
    setWorkspaceId(workspaces[0]?.id ?? ""); setShowForm(true)
  }

  const openEdit = (u: User) => {
    setEditing(u); setEmail(u.email); setPassword(""); setDisplayName(u.display_name)
    setRole(u.role); setWorkspaceId(u.workspace_id ?? ""); setShowForm(true)
  }

  const handleSave = async () => {
    if (!email.trim() || !displayName.trim()) return
    if (!editing && !password.trim()) return
    setSaving(true)
    try {
      if (editing) {
        await api.put(`/v1/admin/users/${editing.id}`, { email, display_name: displayName, role })
        toast.success("User updated")
      } else {
        await api.post("/v1/admin/users", { email, password, display_name: displayName, role, workspace_id: workspaceId })
        toast.success("User created")
      }
      setShowForm(false); fetch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this user?")) return
    try {
      await api.delete(`/v1/admin/users/${id}`)
      toast.success("User deleted")
      fetch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed")
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Users</h2>
        <Button size="sm" onClick={openCreate}><Plus className="h-4 w-4 mr-1" /> Create</Button>
      </div>

      {showForm && (
        <Card className="mb-4">
          <CardContent className="p-4 space-y-3">
            <div className="space-y-1">
              <Label htmlFor="u-email">Email</Label>
              <Input id="u-email" type="email" value={email} onChange={e => setEmail(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="u-name">Display Name</Label>
              <Input id="u-name" value={displayName} onChange={e => setDisplayName(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="u-pw">{editing ? "New Password (leave blank to keep)" : "Password"}</Label>
              <Input id="u-pw" type="password" value={password} onChange={e => setPassword(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="u-role">Role</Label>
                <select
                  id="u-role"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={role}
                  onChange={e => setRole(e.target.value)}
                >
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              {!editing && (
                <div className="space-y-1">
                  <Label htmlFor="u-ws">Workspace</Label>
                  <select
                    id="u-ws"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={workspaceId}
                    onChange={e => setWorkspaceId(e.target.value)}
                  >
                    {workspaces.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                  </select>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <Button onClick={handleSave} disabled={saving || !email.trim() || !displayName.trim()}>
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No users</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="hidden sm:table-cell">Active</TableHead>
                  <TableHead className="w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map(u => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.display_name}</TableCell>
                    <TableCell className="text-sm">{u.email}</TableCell>
                    <TableCell>
                      <Badge variant={u.role === "admin" ? "default" : "secondary"} className="capitalize text-xs">{u.role}</Badge>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      {u.is_active ? <span className="text-green-600">Active</span> : <span className="text-muted-foreground">Inactive</span>}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(u)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(u.id)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
