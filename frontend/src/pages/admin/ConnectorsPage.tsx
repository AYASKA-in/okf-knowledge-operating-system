import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { useAuth } from "@/contexts/AuthContext"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { Plus, Pencil, Trash2, Play, Cable } from "lucide-react"
import { toast } from "sonner"
import type { ConnectorConfig, ConnectorTypeInfo } from "@/types"

const typeConfigFields: Record<string, { key: string; label: string; placeholder: string }[]> = {
  notion: [
    { key: "notion_token", label: "Notion Token", placeholder: "secret_..." },
  ],
  git_webhook: [
    { key: "webhook_secret", label: "Webhook Secret", placeholder: "your-secret" },
  ],
  generic_webhook: [
    { key: "webhook_secret", label: "Webhook Secret", placeholder: "sh-webhook-..." },
  ],
}

export default function ConnectorsPage() {
  const { activeWorkspaceId } = useAuth()
  const [connectors, setConnectors] = useState<ConnectorConfig[]>([])
  const [types, setTypes] = useState<ConnectorTypeInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<ConnectorConfig | null>(null)
  const [type, setType] = useState("notion")
  const [label, setLabel] = useState("")
  const [configValues, setConfigValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)

  const wid = activeWorkspaceId ?? ""

  const fetch = () => {
    if (!wid) return
    setLoading(true)
    Promise.all([
      api.get<ConnectorConfig[]>(`/v1/admin/connectors?workspace_id=${wid}`),
      api.get<ConnectorTypeInfo[]>("/v1/admin/connectors/types"),
    ])
      .then(([conns, t]) => { setConnectors(conns); setTypes(t) })
      .catch(() => toast.error("Failed to load connectors"))
      .finally(() => setLoading(false))
  }

  useEffect(() => { if (wid) fetch() }, [wid])

  const openCreate = () => {
    setEditing(null); setType(types[0]?.type ?? "notion"); setLabel(""); setConfigValues({}); setShowForm(true)
  }

  const openEdit = (c: ConnectorConfig) => {
    setEditing(c); setType(c.connector_type); setLabel(c.label ?? "")
    const vals: Record<string, string> = {}
    for (const field of typeConfigFields[c.connector_type] ?? []) {
      vals[field.key] = String(c.config[field.key] ?? "")
    }
    setConfigValues(vals); setShowForm(true)
  }

  const handleSave = async () => {
    if (!wid) return
    setSaving(true)
    try {
      const config: Record<string, string> = {}
      for (const field of typeConfigFields[type] ?? []) {
        config[field.key] = configValues[field.key] ?? ""
      }
      const body = { connector_type: type, label: label || undefined, config }
      if (editing) {
        await api.put(`/v1/admin/connectors/${editing.id}`, { label: label || undefined, config })
        toast.success("Connector updated")
      } else {
        await api.post(`/v1/admin/connectors?workspace_id=${wid}`, body)
        toast.success("Connector created")
      }
      setShowForm(false); fetch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this connector?")) return
    try {
      await api.delete(`/v1/admin/connectors/${id}`)
      toast.success("Connector deleted")
      fetch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed")
    }
  }

  const handleTest = async (id: string) => {
    setTestingId(id)
    try {
      await api.post(`/v1/admin/connectors/${id}/test`)
      toast.success("Connector test passed")
      fetch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Test failed")
    } finally {
      setTestingId(null)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Connectors</h2>
        <Button size="sm" onClick={openCreate} disabled={!wid}>
          <Plus className="h-4 w-4 mr-1" /> Add Connector
        </Button>
      </div>

      {showForm && (
        <Card className="mb-4">
          <CardContent className="p-4 space-y-3">
            {!editing && (
              <div className="space-y-1">
                <Label>Type</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={type}
                  onChange={e => { setType(e.target.value); setConfigValues({}) }}
                >
                  {types.map(t => <option key={t.type} value={t.type}>{t.label || t.type}</option>)}
                  {types.length === 0 && (
                    <>
                      <option value="notion">Notion</option>
                      <option value="git_webhook">Git Webhook</option>
                      <option value="generic_webhook">Generic Webhook</option>
                    </>
                  )}
                </select>
              </div>
            )}
            <div className="space-y-1">
              <Label>Label</Label>
              <Input value={label} onChange={e => setLabel(e.target.value)} placeholder="My connector" />
            </div>
            {(typeConfigFields[type] ?? []).map(field => (
              <div key={field.key} className="space-y-1">
                <Label>{field.label}</Label>
                <Input
                  value={configValues[field.key] ?? ""}
                  onChange={e => setConfigValues(v => ({ ...v, [field.key]: e.target.value }))}
                  placeholder={field.placeholder}
                />
              </div>
            ))}
            <div className="flex gap-2">
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Connector Configurations</CardTitle>
          <CardDescription>Manage integrations with Notion, GitHub, and custom webhooks</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : connectors.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Cable className="h-12 w-12 mx-auto mb-4 opacity-30" />
              <p>No connectors configured</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden sm:table-cell">Active</TableHead>
                  <TableHead className="w-28"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {connectors.map(c => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">{c.connector_type}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{c.label || "—"}</TableCell>
                    <TableCell className="text-sm">
                      {c.last_status === "ok" && <span className="text-green-600">OK</span>}
                      {c.last_status === "error" && <span className="text-destructive text-xs">{c.last_error?.slice(0, 40)}</span>}
                      {!c.last_status && <span className="text-muted-foreground text-xs">Not tested</span>}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      {c.is_active ? <span className="text-green-600">Yes</span> : <span className="text-muted-foreground">No</span>}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleTest(c.id)} disabled={testingId === c.id}>
                          <Play className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(c)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(c.id)}>
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
