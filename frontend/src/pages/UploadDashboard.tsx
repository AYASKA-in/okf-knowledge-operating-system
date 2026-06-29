import { useEffect, useRef, useState, useCallback } from "react"
import { api } from "@/lib/api"
import { Layout } from "@/components/Layout"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { Upload, RefreshCw, FileText, CheckCircle2, XCircle, Clock, Loader2 } from "lucide-react"
import { toast } from "sonner"
import type { IngestJob } from "@/types"

const statusIcon: Record<string, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-muted-foreground" />,
  running: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />,
  done: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-destructive" />,
}

const statusVariant: Record<string, "outline" | "secondary" | "default" | "destructive"> = {
  pending: "outline",
  running: "secondary",
  done: "default",
  failed: "destructive",
}

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  )
}

function hasActiveJobs(jobs: IngestJob[]) {
  return jobs.some(j => j.status === "pending" || j.status === "running")
}

export default function UploadDashboard() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [jobs, setJobs] = useState<IngestJob[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const prevStatusRef = useRef<Map<string, string>>(new Map())

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.get<{ items: IngestJob[]; total: number }>("/v1/ingest/jobs?size=50")
      setJobs(() => {
        data.items.forEach(job => {
          const prevStatus = prevStatusRef.current.get(job.id)
          if (prevStatus && prevStatus !== job.status) {
            if (job.status === "done") toast.success(`Ingest complete: ${job.file_name || job.id.slice(0, 8)}`)
            if (job.status === "failed") toast.error(`Ingest failed: ${job.error_message?.slice(0, 60)}`)
          }
          prevStatusRef.current.set(job.id, job.status)
        })
        return data.items
      })
    } catch { /* ignore polling errors */ }
  }, [])

  // Poll only when there are active jobs
  useEffect(() => {
    fetchJobs().finally(() => setLoading(false))
  }, [fetchJobs])

  useEffect(() => {
    if (!hasActiveJobs(jobs)) return
    const id = setInterval(fetchJobs, 2000)
    return () => clearInterval(id)
  }, [fetchJobs, jobs])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append("file", file)
      await api.upload<{ job_id: string }>("/v1/ingest/upload", formData)
      toast.success(`${file.name} uploaded — processing started`)
      fetchJobs()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleRetry = async (jobId: string) => {
    try {
      await api.post(`/v1/ingest/jobs/${jobId}/retry`)
      toast.success("Job retry queued")
      fetchJobs()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Retry failed")
    }
  }

  return (
    <Layout title="Upload & Ingest">
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Supported Formats</CardTitle>
          <CardDescription>Markdown (.md), PDF (.pdf), Word (.docx), Excel (.xlsx), HTML (.html)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".md,.pdf,.docx,.xlsx,.html,.htm"
              className="hidden"
              onChange={handleUpload}
            />
            <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
              <Upload className="h-4 w-4 mr-1" />
              {uploading ? "Uploading..." : "Upload File"}
            </Button>
            <p className="text-xs text-muted-foreground">Max 100 MB per file</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Ingest Jobs</CardTitle>
            <Button variant="ghost" size="sm" onClick={fetchJobs} disabled={loading}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <TableSkeleton />
          ) : jobs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-30" />
              <p>No ingest jobs yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>File / Source</TableHead>
                    <TableHead className="hidden sm:table-cell">Created</TableHead>
                    <TableHead>Results</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map(job => (
                    <TableRow key={job.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {statusIcon[job.status]}
                          <Badge variant={statusVariant[job.status]} className="capitalize text-xs">
                            {job.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm max-w-[180px] truncate">
                        {job.file_name || job.connector_type || "—"}
                        {job.file_size && (
                          <span className="text-xs text-muted-foreground ml-1">
                            ({(job.file_size / 1024).toFixed(0)} KB)
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground hidden sm:table-cell">
                        {new Date(job.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm">
                        {job.status === "done" && (
                          <span className="text-green-600">
                            {job.concepts_created ?? 0} created
                            {(job.duplicates_skipped ?? 0) > 0 && ` (${job.duplicates_skipped} dupes)`}
                          </span>
                        )}
                        {job.status === "failed" && (
                          <span className="text-destructive text-xs max-w-[160px] inline-block truncate">
                            {job.error_message}
                          </span>
                        )}
                        {job.status === "pending" && <span className="text-muted-foreground text-xs">Queued</span>}
                        {job.status === "running" && <span className="text-blue-500 text-xs">Processing...</span>}
                      </TableCell>
                      <TableCell>
                        {(job.status === "failed") && (
                          <Button variant="ghost" size="sm" onClick={() => handleRetry(job.id)}>
                            Retry
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </Layout>
  )
}
