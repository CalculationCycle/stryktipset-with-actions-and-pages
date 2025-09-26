import os
from supabase import create_client, Client
from typing import Optional

class SupabaseClient:
    def __init__(self, use_service_key: bool = False):
        """
        Initialize Supabase client
        
        Args:
            use_service_key: If True, uses service role key (for GitHub Actions)
                           If False, uses anon key (for web frontend)
        """
        self.url = os.getenv('SUPABASE_URL')
        
        if not self.url:
            raise ValueError("SUPABASE_URL environment variable is required")
        
        if use_service_key:
            # Use service key for backend operations (GitHub Actions)
            self.key = os.getenv('SUPABASE_SERVICE_KEY')
            if not self.key:
                raise ValueError("SUPABASE_SERVICE_KEY environment variable is required")
        else:
            # Use anon key for frontend operations
            self.key = os.getenv('SUPABASE_ANON_KEY')
            if not self.key:
                raise ValueError("SUPABASE_ANON_KEY environment variable is required")
        
        self.supabase: Client = create_client(self.url, self.key)
    
    def get_client(self) -> Client:
        """Return the Supabase client instance"""
        return self.supabase
    
    def test_connection(self) -> bool:
        """Test if connection to Supabase is working"""
        try:
            # Try to execute a simple query
            result = self.supabase.table('test_table').select("*").limit(1).execute()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def create_tables_if_not_exist(self):
        """Create necessary tables for Stryktipset data"""
        try:
            # This would typically be done via Supabase SQL editor
            # But we can check if tables exist
            print("Checking database tables...")
            
            # Check if predictions table exists
            try:
                self.supabase.table('predictions').select("*").limit(1).execute()
                print("✓ Predictions table exists")
            except:
                print("⚠ Predictions table not found - create it in Supabase dashboard")
            
            # Check if matches table exists  
            try:
                self.supabase.table('matches').select("*").limit(1).execute()
                print("✓ Matches table exists")
            except:
                print("⚠ Matches table not found - create it in Supabase dashboard")
                
        except Exception as e:
            print(f"Error checking tables: {e}")

# Convenience functions
def get_supabase_client(use_service_key: bool = False) -> Client:
    """Get a Supabase client instance"""
    client = SupabaseClient(use_service_key=use_service_key)
    return client.get_client()

def get_backend_client() -> Client:
    """Get Supabase client for backend operations (uses service key)"""
    return get_supabase_client(use_service_key=True)

def get_frontend_client() -> Client:
    """Get Supabase client for frontend operations (uses anon key)"""
    return get_supabase_client(use_service_key=False)