#!/usr/bin/env python3
"""Test Salesforce connection with various domain configurations."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from simple_salesforce import Salesforce

# Load environment variables
load_dotenv()

def test_connection(username, password, token, domain):
    """Test SFDC connection with given credentials."""
    try:
        print(f"\nTesting with domain: '{domain}'")
        sf = Salesforce(
            username=username,
            password=password,
            security_token=token,
            domain=domain
        )
        
        # Test query
        result = sf.query("SELECT COUNT() FROM Case")
        count = result['totalSize']
        
        print(f"✅ SUCCESS! Connected to Salesforce")
        print(f"   Found {count} total cases")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def main():
    """Test various SFDC connection configurations."""
    username = os.getenv('SFDC_USERNAME')
    password = os.getenv('SFDC_PASSWORD')
    token = os.getenv('SFDC_SECURITY_TOKEN')
    
    print("=" * 60)
    print("SALESFORCE CONNECTION TEST")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print(f"Token: {token[:4]}...{token[-4:] if token and len(token) > 8 else 'NOT SET'}")
    
    # Test different domain configurations
    domains_to_test = [
        'login',  # Standard production
        'test',   # Sandbox
        'algoleap-d-dev-ed.develop.my',  # Your current setting
        'algoleap-d-dev-ed.my',  # Alternative format
    ]
    
    success = False
    for domain in domains_to_test:
        if test_connection(username, password, token, domain):
            print(f"\n🎉 Working domain configuration: SFDC_DOMAIN={domain}")
            print("\nUpdate your .env file with this domain setting.")
            success = True
            break
    
    if not success:
        print("\n" + "=" * 60)
        print("❌ ALL CONNECTION ATTEMPTS FAILED")
        print("=" * 60)
        print("\nTroubleshooting steps:")
        print("1. Verify your username is correct")
        print("2. Verify your password is correct (case-sensitive)")
        print("3. Get a fresh security token:")
        print("   - Login to Salesforce")
        print("   - Go to: Setup → My Personal Information → Reset My Security Token")
        print("   - Check your email for the new token")
        print("4. Check if your account is locked or API access is disabled")
        print("\nFor Developer Edition, domain is usually 'login'")
        print("For Sandbox, domain is usually 'test'")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())