import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { api } from "@/lib/api"
import { useAuth } from "@/contexts/AuthContext"
import { Layout } from "@/components/Layout"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Search, ZoomIn, ZoomOut, RotateCcw } from "lucide-react"
import * as d3 from "d3"
import type { Node, Edge as EdgeType } from "@/types"

interface GraphNode extends d3.SimulationNodeDatum {
  id: string
  title: string
  node_type: string
}

interface GraphEdge {
  source: string | GraphNode
  target: string | GraphNode
  relationship: string
}

function GraphSkeleton() {
  return (
    <Card>
      <CardContent className="p-6">
        <Skeleton className="h-[600px] w-full rounded" />
      </CardContent>
    </Card>
  )
}

export default function GraphView() {
  const navigate = useNavigate()
  const { activeWorkspaceId } = useAuth()
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [conceptId, setConceptId] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [nodeCount, setNodeCount] = useState(0)
  const [edgeCount, setEdgeCount] = useState(0)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  useEffect(() => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    const width = svgRef.current.clientWidth || 800
    const height = 600

    svg.selectAll("*").remove()
    svg.append("text")
      .attr("x", width / 2).attr("y", height / 2)
      .attr("text-anchor", "middle").attr("fill", "currentColor")
      .attr("class", "text-muted-foreground text-sm")
      .text("Enter a concept ID above to visualize")
  }, [])

  const loadGraph = async () => {
    if (!conceptId.trim()) return
    if (!activeWorkspaceId) { setError("Select a workspace first"); return }
    setLoading(true)
    setError("")
    try {
      const data = await api.get<{ nodes: Node[]; edges: EdgeType[] }>(`/v1/knowledge/${conceptId}/graph?workspace_id=${activeWorkspaceId}&depth=2`)

      if (!svgRef.current) return
      const svg = d3.select(svgRef.current)
      svg.selectAll("*").remove()

      const width = svgRef.current.clientWidth || 800
      const height = 600

      if (data.nodes.length === 0) {
        svg.append("text")
          .attr("x", width / 2).attr("y", height / 2)
          .attr("text-anchor", "middle").attr("fill", "currentColor")
          .attr("class", "text-muted-foreground text-sm")
          .text("No graph data found for this concept")
        setLoading(false)
        return
      }

      setNodeCount(data.nodes.length)
      setEdgeCount(data.edges.length)

      const nodes: GraphNode[] = data.nodes.map(n => ({
        id: n.id,
        title: n.title,
        node_type: n.node_type,
      }))

      const nodeMap = new Map(nodes.map(n => [n.id, n]))
      const links: GraphEdge[] = data.edges
        .filter(e => nodeMap.has(e.source_id) && nodeMap.has(e.target_id))
        .map(e => ({ source: e.source_id, target: e.target_id, relationship: e.relationship }))

      // Zoom behavior
      const g = svg.append("g")
      zoomRef.current = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform)
        })

      svg.call(zoomRef.current)

      const simulation = d3.forceSimulation<GraphNode>(nodes)
        .force("link", d3.forceLink<GraphNode, GraphEdge>(links).id(d => d.id).distance(120))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(40))

      const color = d3.scaleOrdinal(d3.schemeCategory10)
      const nodeTypes = [...new Set(nodes.map(n => n.node_type))]
      const colorMap = new Map(nodeTypes.map((t, i) => [t, color(String(i))]))

      const link = g.append("g")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke", "currentColor")
        .attr("stroke-opacity", 0.3)
        .attr("stroke-width", 1.5)

      const linkLabel = g.append("g")
        .selectAll("text")
        .data(links)
        .join("text")
        .text(d => d.relationship)
        .attr("font-size", 9)
        .attr("fill", "currentColor")
        .attr("fill-opacity", 0.5)
        .attr("text-anchor", "middle")

      const group = g.append("g")
        .selectAll("g")
        .data(nodes)
        .join("g")
        .style("cursor", "pointer")
        .on("click", (_event, d) => navigate(`/concept/${d.id}`))

      group.append("circle")
        .attr("r", 22)
        .attr("fill", d => colorMap.get(d.node_type) || "#666")
        .attr("stroke", "#fff")
        .attr("stroke-width", 2.5)

      group.append("text")
        .text(d => d.title.length > 18 ? d.title.slice(0, 18) + "..." : d.title)
        .attr("text-anchor", "middle")
        .attr("dy", 38)
        .attr("font-size", 10)
        .attr("fill", "currentColor")
        .attr("class", "select-none")

      simulation.on("tick", () => {
        link
          .attr("x1", d => (d.source as GraphNode).x!)
          .attr("y1", d => (d.source as GraphNode).y!)
          .attr("x2", d => (d.target as GraphNode).x!)
          .attr("y2", d => (d.target as GraphNode).y!)
        linkLabel
          .attr("x", d => ((d.source as GraphNode).x! + (d.target as GraphNode).x!) / 2)
          .attr("y", d => ((d.source as GraphNode).y! + (d.target as GraphNode).y!) / 2)
        group.attr("transform", d => `translate(${d.x},${d.y})`)
      })

      // Legend
      const legendG = svg.append("g")
        .attr("transform", `translate(${width - 160}, 20)`)
      let legendY = 0
      for (const [type, c] of colorMap) {
        legendG.append("circle").attr("cx", 0).attr("cy", legendY).attr("r", 5).attr("fill", c)
        legendG.append("text").attr("x", 12).attr("y", legendY + 4)
          .attr("font-size", 10).attr("fill", "currentColor").text(type)
        legendY += 20
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph")
    } finally {
      setLoading(false)
    }
  }

  const handleZoomIn = () => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.3)
    }
  }
  const handleZoomOut = () => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 0.7)
    }
  }
  const handleReset = () => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.transform, d3.zoomIdentity)
    }
  }

  return (
    <Layout title="Knowledge Graph">
      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Enter concept ID to explore..."
            className="pl-10"
            value={conceptId}
            onChange={e => setConceptId(e.target.value)}
            onKeyDown={e => e.key === "Enter" && loadGraph()}
          />
        </div>
        <Button onClick={loadGraph} disabled={loading}>
          {loading ? "Loading..." : "Explore"}
        </Button>
      </div>

      {error && <p className="text-sm text-destructive mb-4">{error}</p>}

      {loading ? (
        <GraphSkeleton />
      ) : (
        <Card>
          <CardContent className="p-0 relative">
            {nodeCount > 0 && (
              <div className="absolute top-3 left-3 z-10 flex gap-2">
                <Badge variant="outline">{nodeCount} nodes</Badge>
                <Badge variant="outline">{edgeCount} edges</Badge>
              </div>
            )}
            <div className="absolute top-3 right-3 z-10 flex gap-1" ref={containerRef}>
              <Button variant="secondary" size="icon" className="h-8 w-8" onClick={handleZoomIn} title="Zoom in">
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button variant="secondary" size="icon" className="h-8 w-8" onClick={handleZoomOut} title="Zoom out">
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button variant="secondary" size="icon" className="h-8 w-8" onClick={handleReset} title="Reset view">
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
            <svg ref={svgRef} className="w-full" style={{ height: 600 }} />
          </CardContent>
        </Card>
      )}
    </Layout>
  )
}
