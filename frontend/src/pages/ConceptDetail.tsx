import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { api } from "@/lib/api"
import { useAuth } from "@/contexts/AuthContext"
import { Layout } from "@/components/Layout"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { ExternalLink } from "lucide-react"
import type { Node, Edge } from "@/types"

function DetailSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-48 mt-1" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
      </CardContent>
    </Card>
  )
}

export default function ConceptDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeWorkspaceId } = useAuth()
  const [node, setNode] = useState<Node | null>(null)
  const [edges, setEdges] = useState<Edge[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    if (!activeWorkspaceId) return
    Promise.all([
      api.get<Node>(`/v1/knowledge/${id}`),
      api.get<{ nodes?: Node[]; edges: Edge[] }>(`/v1/knowledge/${id}/edges?workspace_id=${activeWorkspaceId}`),
    ])
      .then(([nodeData, edgeData]) => {
        setNode(nodeData)
        setEdges(edgeData.edges || [])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id, activeWorkspaceId])

  if (loading) {
    return (
      <Layout showBack title="Loading...">
        <DetailSkeleton />
      </Layout>
    )
  }

  if (!node) {
    return (
      <Layout showBack title="Not Found">
        <div className="text-center py-16">
          <p className="text-muted-foreground mb-4">Concept not found</p>
          <Button onClick={() => navigate("/")}>Back to Knowledge Base</Button>
        </div>
      </Layout>
    )
  }

  return (
    <Layout showBack title={node.title}>
      <Card>
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-2xl">{node.title}</CardTitle>
              {node.subtitle && <CardDescription className="mt-1">{node.subtitle}</CardDescription>}
            </div>
            <Badge className="shrink-0">{node.node_type}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {node.tags && node.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {node.tags.map(tag => (
                <span key={tag} className="text-xs bg-muted px-2 py-0.5 rounded-full">{tag}</span>
              ))}
            </div>
          )}

          {(node.source_connector || node.chunk_index !== null) && (
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {node.source_connector && <span>Source: {node.source_connector}</span>}
              {node.source_original_id && <span>ID: {node.source_original_id}</span>}
              {node.chunk_index !== null && node.chunk_index !== undefined && (
                <Badge variant="outline" className="text-xs">Part {node.chunk_index + 1}</Badge>
              )}
            </div>
          )}

          <Separator />

          {node.body_text ? (
            <div className="prose prose-sm max-w-none whitespace-pre-wrap leading-relaxed">
              {node.body_text}
            </div>
          ) : (
            <p className="text-muted-foreground italic">No body content</p>
          )}

          {edges.length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-medium mb-3">Relationships ({edges.length})</h3>
                <div className="space-y-2">
                  {edges.map(edge => {
                    const isOutbound = edge.source_id === id
                    const relatedId = isOutbound ? edge.target_id : edge.source_id
                    const label = isOutbound ? edge.relationship : `← ${edge.relationship}`
                    return (
                      <div key={edge.id} className="flex items-center gap-2 text-sm p-2 bg-muted/30 rounded">
                        <span className="text-muted-foreground capitalize">{label}</span>
                        <Button
                          variant="link"
                          size="sm"
                          className="h-auto p-0"
                          onClick={() => navigate(`/concept/${relatedId}`)}
                        >
                          {relatedId.slice(0, 8)}... <ExternalLink className="h-3 w-3 ml-1" />
                        </Button>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </Layout>
  )
}
