export interface Project {
  id: string; name: string; slug: string; description: string; status: string; risk_level: string;
  icon: string; accent: string; owner_user_id?: string | null;
  kb_count?: number; doc_count?: number; chunk_count?: number; updated_at?: string;
}
export interface Governance {
  risk_level: string; pii_risk?: string; sensitive_data?: boolean; high_risk_approval?: boolean;
  stale_handling?: string; citation_required?: boolean; strict_grounding_required?: boolean;
  external_source_allowed?: boolean; tenant_isolation?: boolean; audit_logging?: boolean;
  redaction?: boolean; right_to_be_forgotten?: boolean; document_expiration_days?: number;
  source_trust_level?: string; logs_retrieval?: boolean; exclude_stale_documents?: boolean;
}
export interface KnowledgeBase {
  id: string; name: string; slug: string; description: string; project_id?: string | null;
  status: string; risk_level: string; vector_backend: string; embedding_provider: string; embedding_model: string;
  retrieval_strategy: string; chunking_config: any; retrieval_config: any; governance: Governance;
  owner_user_id?: string | null; document_count?: number; chunk_count?: number; retrieval_score?: number | null;
  last_test?: string | null; source_types?: string[]; last_indexed_at?: string | null;
  created_at?: string; updated_at?: string; badges?: string[];
  project?: Project | null; sources?: Source[]; retrieval_tests?: any[]; qa_tests?: any[];
}
export interface Source {
  id: string; knowledge_base_id: string; source_type: string; name: string; description: string;
  status: string; trust_level: string; risk_level: string; documents_imported: number; chunks_created: number;
  last_sync_at?: string | null; config: any;
}
export interface RagDocument {
  id: string; knowledge_base_id: string; source_id: string; title: string; source_ref: string; file_type: string;
  raw_text?: string; metadata: any; status: string; risk_level: string; freshness_status: string;
  chunk_count: number; token_count: number; indexed_at?: string; created_at?: string;
  risk_scan?: { risk_level: string; found: string[]; has_secret: boolean };
}
export interface Chunk {
  id: string; knowledge_base_id: string; document_id: string; chunk_index: number; title: string; content: string;
  metadata: any; tags: string[]; token_count: number; embedding_status: string; citation_ref: any;
  risk_level: string; enabled: boolean; created_at?: string; neighbors?: any[];
}
export interface Retrieved {
  chunk_id: string; title: string; content: string; score: number; reason: string; matched: string[];
  risk_level?: string; stale?: boolean; tags: string[]; citation: any; document_title?: string;
}
export interface RetrievalResult {
  query: string; retrieved: Retrieved[]; excluded: { title: string; reason: string }[];
  assembled_context: string; retrieval_quality_score: number; latency_ms: number; suggestions: string[]; mode: string;
}
export interface Citation { document: string; source: string; chunk_index: number; chunk_id: string; score: number; }
export interface QAResult {
  question: string; answer: string; citations: Citation[]; retrieved: Retrieved[];
  confidence: number; grounding_score: number; missing_evidence: boolean; model_provider: string; model: string;
  metrics: { token_estimate: number; cost_estimate: number; latency_ms: number }; evaluation: any; assembled_context: string;
}
export interface Stats {
  projects: number; kbs: number; documents: number; chunks: number; retrieval_tests: number;
  avg_retrieval: number | null; high_risk: number; storage_kb: number;
}
