import os
import shutil

# Cấu trúc mới
STRUCTURE = {
    'sql/': [
        'current_schema.sql', 'fix_db_schema.sql', 'migrate_schema.sql',
        'migrate_to_schemas.sql', 'migration_step_by_step.sql', 'run_migration.sql',
        'supabase_schema*.sql', 'init_db.sql', 'create_views.sql', 'improved_views.sql',
        'add_last_update*.sql', 'check_*.sql', 'clear_*.sql', 'detect_changes.sql',
        'reset_*.sql', '*.sql'
    ],
    'docs/': [
        '*.md', 'CHECKLIST_N8N.md', 'DOC_ID_EXPLAINED.md', 'ENHANCED_REGEX_SUMMARY.md',
        'FILE_STORAGE_GUIDE.md', 'FINAL_PRODUCTION_SUMMARY.md', 'FORMULA_*.md',
        'HUMAN_IN_THE_LOOP_PIPELINE.md', 'IMPORT_FIX_SUMMARY.md', 'ITERATION_2_SUMMARY.md',
        'LLM_SETUP_GUIDE.md', 'MIGRATE_TNPL_GUIDE.md', 'N8N_*.md', 'QUICKSTART.md',
        'README*.md', 'RESTRUCTURE_PLAN.md', 'RUN_FIX_DB.md', 'SETUP_*.md',
        'SQL_QUERIES_CHEATSHEET.md', 'SUPABASE_SETUP_CHECKLIST.md', 'UPDATE_TARGET_DOC_ID.md',
        'VERSIONING_SUMMARY.md', 'VIEWS_USAGE.md', 'WORKFLOW_*.md', 'q-dev-chat-*.md'
    ],
    'scripts/test/': [
        'test_*.py', 'debug_*.py', 'check_*.py', 'verify_*.py', 'show_results.py'
    ],
    'scripts/crawl/': [
        'crawl_*.py', 'quick_crawl.py', 'simple_crawler.py', 'run_single_url.py'
    ],
    'scripts/extract/': [
        '*_extractor.py', '*_formula*.py', 'extract_*.py', 'format_*.py'
    ],
    'scripts/migration/': [
        'migrate_*.py', 'transform_*.py', 'import_*.py', 'export_*.py',
        'backup_*.py', 'resume_*.py', 'fix_*.py', 'update_*.py', 'restructure.py'
    ],
    'scripts/utils/': [
        'setup_*.py', 'cleanup_*.py', 'clear_*.py', 'save_to_db.py',
        'search_term.py', 'read_full_content.py'
    ],
    'scripts/analysis/': [
        'audit_*.py', 'gap_analyzer.py', 'document_pattern_analyzer.py',
        'human_in_loop_tracker.py', 'pattern_tracker.json'
    ],
    'config/n8n/': [
        'n8n_*.json', 'n8n_*.js', 'n8n_*.py', 'n8n_*.md'
    ],
    'archive/old_tests/': [
        'test_crawl*.py', 'test_selenium*.py', 'test_page*.py',
        'test_hybrid*.py', 'test_single*.py', 'test_with_existing*.py'
    ],
    'archive/debug/': [
        'debug_*.html', 'debug_*.txt', 'debug_*.png', 'debug_*.json',
        'tnpl_sample.txt', 'captcha_*.png'
    ]
}

def move_files():
    moved = []
    errors = []
    
    for target_dir, patterns in STRUCTURE.items():
        os.makedirs(target_dir, exist_ok=True)
        
        for pattern in patterns:
            if '*' in pattern:
                import glob
                files = glob.glob(pattern)
            else:
                files = [pattern] if os.path.exists(pattern) else []
            
            for file in files:
                if os.path.isfile(file) and not file.startswith(('sql/', 'docs/', 'scripts/', 'config/', 'archive/')):
                    try:
                        dest = os.path.join(target_dir, os.path.basename(file))
                        if not os.path.exists(dest):
                            shutil.move(file, dest)
                            moved.append(f"{file} → {dest}")
                    except Exception as e:
                        errors.append(f"Error moving {file}: {e}")
    
    print(f"✓ Moved {len(moved)} files")
    for m in moved[:10]:
        print(f"  {m}")
    if len(moved) > 10:
        print(f"  ... and {len(moved)-10} more")
    
    if errors:
        print(f"\n✗ {len(errors)} errors:")
        for e in errors[:5]:
            print(f"  {e}")

if __name__ == '__main__':
    print("Restructuring project...")
    move_files()
    print("\n✓ Done! Check the new structure.")
