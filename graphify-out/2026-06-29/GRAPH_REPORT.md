# Graph Report - .  (2026-06-29)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 407 nodes · 1140 edges · 22 communities (19 shown, 3 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 169 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `66f5e0ad`
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

## God Nodes (most connected - your core abstractions)
1. `BundleManager` - 68 edges
2. `OKFConcept` - 63 edges
3. `OKFFrontmatter` - 54 edges
4. `TestAdminEndpoints` - 34 edges
5. `Node` - 32 edges
6. `StructurerAgent` - 29 edges
7. `IngestorAgent` - 26 edges
8. `LinkerAgent` - 24 edges
9. `VertexAIClient` - 23 edges
10. `Base` - 22 edges

## Surprising Connections (you probably didn't know these)
- `TestIngestorAgentWithLLM` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestLinkerAgentWithLLM` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestStructurerAgentWithLLM` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestVertexAIClient` --uses--> `ChatAgent`  [INFERRED]
  tests/test_llm.py → app/agents/chat.py
- `TestOKFConceptModel` --uses--> `IngestorAgent`  [INFERRED]
  tests/test_ingestion.py → app/agents/ingestor.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Compliance Framework** — seed_data_sample_bundle_compliance_code_of_conduct, seed_data_sample_bundle_compliance_data_protection, seed_data_sample_bundle_compliance_index [EXTRACTED 0.95]
- **Remote Work Infrastructure** — seed_data_sample_bundle_hr_remote_work_policy, seed_data_sample_bundle_hr_equipment_stipend, seed_data_sample_bundle_compliance_data_protection [INFERRED 0.85]

## Communities (22 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (38): create_edge(), delete_edge(), get_concept_edges(), AsyncSession, ingest_document(), AsyncSession, require_role(), Settings (+30 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (34): chat(), AsyncSession, create_concept(), delete_concept(), get_concept(), get_concept_links(), list_concepts(), AsyncSession (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.13
Nodes (13): login(), AsyncSession, refresh(), get_current_user(), Any, AsyncSession, require_auth(), create_access_token() (+5 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (5): OKFValidator, ValidationResult, main(), CLI tool to validate any OKF bundle directory for spec compliance. Usage: python, TestOKFValidator

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (7): cleanup_temp(), export_bundle(), AsyncSession, FileSystemStore, BackgroundTasks, Path, TestKnowledgeEndpoints

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (6): get_llm_client(), VertexAIClient, TestVertexAIClient, llm_client(), Gated integration tests for Vertex AI.  Requires GCP_PROJECT_ID env var and vali, TestVertexRealLLM

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (4): OKFConcept, OKFFrontmatter, TestBundleManager, TestOKFConceptModel

### Community 8 - "Community 8"
Cohesion: 0.18
Nodes (5): IngestorAgent, Any, TestIngestorAgent, TestOKFConceptAdditional, TestIngestorAgentWithLLM

### Community 9 - "Community 9"
Cohesion: 0.21
Nodes (8): ChatAgent, Any, MockLLMClient, Tests for LLM client and agent LLM integration., Ensure gcp_project_id is empty for fallback tests., Mock LLM client for testing agent LLM integration., reset_settings(), TestChatAgentWithLLM

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (4): Any, StructurerAgent, TestStructurerAgent, TestStructurerAgentWithLLM

### Community 12 - "Community 12"
Cohesion: 0.25
Nodes (14): create_user(), create_workspace(), delete_user(), delete_workspace(), get_audit_logs(), get_user(), get_workspace(), list_users() (+6 more)

### Community 13 - "Community 13"
Cohesion: 0.26
Nodes (3): OKFBundle, BundleError, Exception

### Community 15 - "Community 15"
Cohesion: 0.27
Nodes (10): Code of Conduct, Data Protection Policy, Compliance, Deployment Guide, Development Workflow, Engineering, Equipment Stipend Policy, Human Resources (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.50
Nodes (3): Stores list-of-strings; uses ARRAY(String) on PostgreSQL, JSON elsewhere., StringArray, TypeDecorator

## Knowledge Gaps
- **1 isolated node(s):** `Code of Conduct`
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BundleManager` connect `Community 10` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.264) - this node is a cross-community bridge._
- **Why does `OKFConcept` connect `Community 7` to `Community 0`, `Community 1`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Why does `TestAdminEndpoints` connect `Community 6` to `Community 0`, `Community 10`, `Community 7`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `BundleManager` (e.g. with `ChatAgent` and `LinkerAgent`) actually correct?**
  _`BundleManager` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `OKFConcept` (e.g. with `LinkerAgent` and `StructurerAgent`) actually correct?**
  _`OKFConcept` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `OKFFrontmatter` (e.g. with `StructurerAgent` and `BundleError`) actually correct?**
  _`OKFFrontmatter` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `TestAdminEndpoints` (e.g. with `Base` and `Edge`) actually correct?**
  _`TestAdminEndpoints` has 9 INFERRED edges - model-reasoned connections that need verification._