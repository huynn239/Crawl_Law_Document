-- Tạo views trong public schema để Supabase có thể access
-- Supabase chỉ expose public và graphql_public schemas

-- System tables
CREATE OR REPLACE VIEW public.crawl_url AS SELECT * FROM system.crawl_url;
CREATE OR REPLACE VIEW public.crawl_sessions AS SELECT * FROM system.crawl_sessions;
CREATE OR REPLACE VIEW public.audit_logs AS SELECT * FROM system.audit_logs;

-- TVPL tables
CREATE OR REPLACE VIEW public.document_finals AS SELECT * FROM tvpl.document_finals;
CREATE OR REPLACE VIEW public.document_relations AS SELECT * FROM tvpl.document_relations;
CREATE OR REPLACE VIEW public.document_files AS SELECT * FROM tvpl.document_files;
CREATE OR REPLACE VIEW public.document_versions AS SELECT * FROM tvpl.document_versions;

-- TNPL tables
CREATE OR REPLACE VIEW public.tnpl_terms AS SELECT * FROM tnpl.terms;
CREATE OR REPLACE VIEW public.tnpl_crawl_sessions AS SELECT * FROM tnpl.crawl_sessions;

-- Analytical views (from views schema)
CREATE OR REPLACE VIEW public.documents_overview AS SELECT * FROM views.v_documents_overview;
CREATE OR REPLACE VIEW public.document_relations_view AS SELECT * FROM views.v_document_relations;
CREATE OR REPLACE VIEW public.pending_downloads AS SELECT * FROM views.v_pending_downloads;
CREATE OR REPLACE VIEW public.tnpl_terms_view AS SELECT * FROM views.v_tnpl_terms;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.crawl_url TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.crawl_sessions TO anon, authenticated;
GRANT SELECT, INSERT ON public.audit_logs TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE ON public.document_finals TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.document_relations TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.document_files TO anon, authenticated;
GRANT SELECT, INSERT ON public.document_versions TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE ON public.tnpl_terms TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.tnpl_crawl_sessions TO anon, authenticated;

GRANT SELECT ON public.documents_overview TO anon, authenticated;
GRANT SELECT ON public.document_relations_view TO anon, authenticated;
GRANT SELECT ON public.pending_downloads TO anon, authenticated;
GRANT SELECT ON public.tnpl_terms_view TO anon, authenticated;

-- Reload Supabase schema cache
NOTIFY pgrst, 'reload schema';
