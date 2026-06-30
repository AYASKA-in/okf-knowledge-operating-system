# Graph Report - okf knowledge operating system  (2026-06-30)

## Corpus Check
- 146 files · ~44,065 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1047 nodes · 2661 edges · 59 communities (47 shown, 12 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 302 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c2768d05`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]

## God Nodes (most connected - your core abstractions)
1. `BundleManager` - 92 edges
2. `OKFConcept` - 69 edges
3. `OKFFrontmatter` - 60 edges
4. `ParsedDocument` - 45 edges
5. `Node` - 40 edges
6. `TestAdminEndpoints` - 37 edges
7. `StructurerAgent` - 30 edges
8. `Base` - 30 edges
9. `Section` - 30 edges
10. `TestConnectorEndpoints` - 29 edges

## Surprising Connections (you probably didn't know these)
- `TestIngestorAgentWithLLM` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestLinkerAgentWithLLM` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestStructurerAgentWithLLM` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestVertexAIClient` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestOKFConceptAdditional` --uses--> `IngestorAgent`  [INFERRED]
  tests/test_ingestion.py → app/agents/ingestor.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Compliance Framework** — seed_data_sample_bundle_compliance_code_of_conduct, seed_data_sample_bundle_compliance_data_protection, seed_data_sample_bundle_compliance_index [EXTRACTED 0.95]
- **Remote Work Infrastructure** — seed_data_sample_bundle_hr_remote_work_policy, seed_data_sample_bundle_hr_equipment_stipend, seed_data_sample_bundle_compliance_data_protection [INFERRED 0.85]

## Communities (59 total, 12 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.21
Nodes (13): _background_export(), cleanup_temp(), require_role(), get_db(), get_engine(), get_session_factory(), init_db(), AsyncSession (+5 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (74): create_connector(), create_user(), create_workspace(), delete_connector(), delete_user(), delete_workspace(), get_audit_logs(), get_connector_config() (+66 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (15): login(), AsyncSession, refresh(), get_current_user(), Any, AsyncSession, require_auth(), create_access_token() (+7 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (5): OKFValidator, ValidationResult, main(), CLI tool to validate any OKF bundle directory for spec compliance. Usage: python, TestOKFValidator

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (5): VertexAIClient, TestVertexAIClient, llm_client(), Gated integration tests for Vertex AI.  Requires GCP_PROJECT_ID env var and vali, TestVertexRealLLM

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (27): ABC, MarkdownCleaner, DocumentConnector, Validate config and return a human-readable status message., GenericWebhookConnector, verify_signature(), GitWebhookConnector, NotionConnector (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (5): OKFConcept, OKFFrontmatter, TestBundleManager, TestOKFConceptAdditional, TestOKFConceptModel

### Community 8 - "Community 8"
Cohesion: 0.21
Nodes (4): IngestorAgent, Any, TestIngestorAgent, TestIngestorAgentWithLLM

### Community 9 - "Community 9"
Cohesion: 0.21
Nodes (8): ChatAgent, Any, MockLLMClient, Tests for LLM client and agent LLM integration., Ensure gcp_project_id is empty for fallback tests., Mock LLM client for testing agent LLM integration., reset_settings(), TestChatAgentWithLLM

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (4): chat(), AsyncSession, BundleManager, test_db()

### Community 11 - "Community 11"
Cohesion: 0.18
Nodes (4): Any, StructurerAgent, TestStructurerAgent, TestStructurerAgentWithLLM

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (29): Settings, PipelineContext, PipelineOrchestrator, StageResult, PipelineStage, Any, StageError, ChunkStage (+21 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (36): Code of Conduct, Core Principles, Enforcement, Reporting Violations, Data Classification, Data Protection Policy, Handling Requirements, Remote Work (+28 more)

### Community 16 - "Community 16"
Cohesion: 0.50
Nodes (3): Stores list-of-strings; uses ARRAY(String) on PostgreSQL, JSON elsewhere., StringArray, TypeDecorator

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (9): detect_format(), parse_document(), Tests for document parsers., TestDetectFormat, TestDocxParser, TestHtmlParser, TestParseDocumentIntegration, TestPdfParser (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (17): Base, AuditAction, AuditLog, ConnectorConfig, EdgeType, ExportJob, ExportJobStatus, IngestJobStatus (+9 more)

### Community 24 - "Community 24"
Cohesion: 0.11
Nodes (21): AdminLayout(), adminNavItems, ChatMessage(), ChatMessageProps, Citation, Props, State, LayoutProps (+13 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (22): AdminGuard(), ProtectedRoute(), PublicRoute(), ChatInput(), ChatInputProps, ErrorBoundary, Layout(), AuthProvider() (+14 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (27): dependencies, clsx, d3, lucide-react, react, react-dom, react-router-dom, sonner (+19 more)

### Community 27 - "Community 27"
Cohesion: 0.19
Nodes (15): Badge(), BadgeProps, badgeVariants, Label, Table, TableBody, TableCell, TableHead (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (7): create_concept(), Edge, Node, NodeStatus, TestEdgeEndpoints, TestGraphEndpoints, TestSearchEndpoints

### Community 29 - "Community 29"
Cohesion: 0.19
Nodes (7): ChunkerAgent, _estimate_tokens(), _hash_text(), Any, _make_section(), Unit tests for ChunkerAgent., TestChunkerAgent

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (23): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+15 more)

### Community 31 - "Community 31"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, ignoreDeprecations, jsx, lib, module, moduleDetection (+12 more)

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (18): _background_ingest(), generic_webhook(), get_ingest_job(), github_webhook(), ingest_document(), ingest_upload(), list_ingest_jobs(), AsyncSession (+10 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (12): Input, useDebounce(), GraphEdge, GraphNode, KnowledgeList(), AuditLogEntry, AuthResponse, Edge (+4 more)

### Community 36 - "Community 36"
Cohesion: 0.30
Nodes (10): AuthContext, AuthContextValue, api, clearTokens(), getAccessToken(), loadTokens(), request(), setTokens() (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (11): API Endpoints (37 routes), Architecture, Config, Goal, Infrastructure, Key Features, Notable Fixes, OKF Knowledge Operating System (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.36
Nodes (6): Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle

### Community 39 - "Community 39"
Cohesion: 0.25
Nodes (7): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 41 - "Community 41"
Cohesion: 0.40
Nodes (4): Dialog, DialogDescription, DialogHeader, DialogTitle

### Community 42 - "Community 42"
Cohesion: 0.50
Nodes (4): create_edge(), delete_edge(), get_concept_edges(), AsyncSession

### Community 43 - "Community 43"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 44 - "Community 44"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 45 - "Community 45"
Cohesion: 0.50
Nodes (3): For /graphify explain, For /graphify path, graphify reference: query, path, explain

### Community 46 - "Community 46"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **151 isolated node(s):** `$schema`, `plugin`, `name`, `private`, `version` (+146 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BundleManager` connect `Community 10` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 23`, `Community 28`, `Community 32`, `Community 34`, `Community 35`, `Community 40`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Why does `ChunkerAgent` connect `Community 29` to `Community 8`, `Community 12`, `Community 6`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `OKFConcept` connect `Community 7` to `Community 0`, `Community 1`, `Community 2`, `Community 34`, `Community 35`, `Community 4`, `Community 5`, `Community 40`, `Community 8`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 9`, `Community 23`, `Community 28`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `BundleManager` (e.g. with `ChatAgent` and `LinkerAgent`) actually correct?**
  _`BundleManager` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `OKFConcept` (e.g. with `LinkerAgent` and `StructurerAgent`) actually correct?**
  _`OKFConcept` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `OKFFrontmatter` (e.g. with `StructurerAgent` and `IndexStage`) actually correct?**
  _`OKFFrontmatter` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `ParsedDocument` (e.g. with `DocumentConnector` and `GenericWebhookConnector`) actually correct?**
  _`ParsedDocument` has 12 INFERRED edges - model-reasoned connections that need verification._