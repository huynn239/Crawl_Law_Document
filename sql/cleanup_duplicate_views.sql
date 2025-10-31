-- Xóa các view trùng lặp không cần thiết trong public schema

DROP VIEW IF EXISTS public.document_history;
DROP VIEW IF EXISTS public.relations_view;
DROP VIEW IF EXISTS public.sessions_summary;
DROP VIEW IF EXISTS public.stats_overview;
DROP VIEW IF EXISTS public.stats_by_type;
DROP VIEW IF EXISTS public.stats_by_relation_type;
DROP VIEW IF EXISTS public.files_stats;
DROP VIEW IF EXISTS public.v_documents_overview;
DROP VIEW IF EXISTS public.v_pending_downloads;
DROP VIEW IF EXISTS public.v_tnpl_terms;
DROP VIEW IF EXISTS public.v_document_relations;

-- Reload Supabase schema cache
NOTIFY pgrst, 'reload schema';
