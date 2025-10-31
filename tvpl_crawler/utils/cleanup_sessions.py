"""Cleanup stale RUNNING sessions"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get RUNNING sessions older than 2 hours
cutoff = (datetime.now() - timedelta(hours=2)).isoformat()
stale = supabase.table('crawl_sessions')\
    .select('session_id, started_at')\
    .eq('status', 'RUNNING')\
    .lt('started_at', cutoff)\
    .execute()

if not stale.data:
    print("No stale sessions")
else:
    for s in stale.data:
        supabase.table('crawl_sessions').update({
            'status': 'FAILED',
            'completed_at': datetime.now().isoformat()
        }).eq('session_id', s['session_id']).execute()
        print(f"✓ Cleaned session #{s['session_id']}")
    print(f"\nCleaned {len(stale.data)} sessions")
