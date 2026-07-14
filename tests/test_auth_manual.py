import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth import AuthenticationProvider

def test_auth():
    print("Initializing AuthenticationProvider...")
    # headless=False lets you interactively sign in if needed
    provider = AuthenticationProvider()
    
    print("Attempting to acquire token (this may open a browser window)...")
    try:
        token = provider.get_access_token()
        print("\n=== Success! ===")
        print(f"Token acquired successfully.")
        print(f"Token length: {len(token)}")
        print(f"Token snippet: {token[:15]}...")
        
        print("\nTesting requests.Session decoration...")
        session = provider.get_session()
        print(f"Session headers: {list(session.headers.keys())}")
        print(f"Session cookies: {list(session.cookies.keys())}")
    except Exception as e:
        print(f"\n=== Authentication Failed ===")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_auth()
