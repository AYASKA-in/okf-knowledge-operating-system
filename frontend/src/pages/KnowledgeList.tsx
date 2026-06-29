import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { useNavigate } from "react-router-dom"
import { useDebounce } from "@/hooks/useDebounce"
import { Layout } from "@/components/Layout"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Search, FileText } from "lucide-react"
import type { Node, PaginatedResponse } from "@/types"

function ListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Card key={i}>
          <CardHeader className="p-4 pb-2">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-3 w-32 mt-1" />
          </CardHeader>
          <CardContent className="p-4 pt-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4 mt-1" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default function KnowledgeList() {
  const navigate = useNavigate()
  const [nodes, setNodes] = useState<Node[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const debouncedSearch = useDebounce(search, 300)
  const [loading, setLoading] = useState(true)
  const pageSize = 20

  useEffect(() => {
    setLoading(true)
    const query = debouncedSearch
      ? `/v1/knowledge?search=${encodeURIComponent(debouncedSearch)}&page=${page}&size=${pageSize}`
      : `/v1/knowledge?page=${page}&size=${pageSize}`
    api.get<PaginatedResponse<Node>>(query)
      .then(data => {
        setNodes(data.items)
        setTotal(data.total)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page, debouncedSearch])

  return (
    <Layout title="Knowledge Base">
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search concepts..."
          className="pl-10"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
        />
      </div>

      {loading ? (
        <ListSkeleton />
      ) : nodes.length === 0 ? (
        <div className="text-center py-16">
          <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/30" />
          <p className="text-muted-foreground mb-4">No concepts found.</p>
          <Button onClick={() => navigate("/upload")}>Upload Documents</Button>
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground mb-4">{total} concept{total !== 1 ? "s" : ""}</p>
          <div className="grid gap-3">
            {nodes.map(node => (
              <Card
                key={node.id}
                className="cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => navigate(`/concept/${node.id}`)}
              >
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <CardTitle className="text-base truncate">{node.title}</CardTitle>
                      {node.subtitle && (
                        <CardDescription className="text-xs mt-0.5 truncate">{node.subtitle}</CardDescription>
                      )}
                    </div>
                    <Badge variant="outline" className="text-xs shrink-0">{node.node_type}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-2">
                  {node.tags && node.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {node.tags.map(tag => (
                        <span key={tag} className="text-xs bg-muted px-2 py-0.5 rounded-full">{tag}</span>
                      ))}
                    </div>
                  )}
                  {node.body_text && (
                    <p className="text-sm text-muted-foreground line-clamp-2">{node.body_text}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          {total > pageSize && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {Math.ceil(total / pageSize)}
              </span>
              <Button variant="outline" size="sm" disabled={page >= Math.ceil(total / pageSize)} onClick={() => setPage(p => p + 1)}>
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </Layout>
  )
}
