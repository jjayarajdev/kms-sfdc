# Salesforce Connection Guide

## Common Connection Issues and Solutions

### 1. Invalid Login Error

If you're getting `INVALID_LOGIN: Invalid username, password, security token; or user locked out`, check:

#### **Verify Credentials Format**

1. **Username**: Should be your full Salesforce username (e.g., `user@company.com`)
2. **Password**: Your Salesforce password (case-sensitive)
3. **Security Token**: Get from Salesforce:
   - Go to: Setup → Personal Setup → My Personal Information → Reset My Security Token
   - Check your email for the new token
4. **Domain**: 
   - For Developer Edition: `login` (default)
   - For Sandbox: `test`
   - For Custom Domain: Just the prefix (e.g., `mycompany` for `mycompany.my.salesforce.com`)

#### **Common Domain Formats**

```bash
# Developer Edition
SFDC_DOMAIN=login

# Sandbox
SFDC_DOMAIN=test

# Custom Domain (if your URL is https://mycompany.my.salesforce.com)
SFDC_DOMAIN=mycompany.my

# Lightning Domain (if your URL is https://mycompany.lightning.force.com)
SFDC_DOMAIN=mycompany.my
```

### 2. How to Get Your Security Token

1. Log into Salesforce
2. Click on your profile picture → Settings
3. Navigate to: Personal → Reset My Security Token
4. Click "Reset Security Token"
5. Check your email for the new token

### 3. Testing Connection Manually

```python
from simple_salesforce import Salesforce

# Test your credentials directly
sf = Salesforce(
    username='your_username@company.com',
    password='your_password',
    security_token='your_security_token',
    domain='login'  # or 'test' for sandbox
)

print("Connected successfully!")
```

### 4. Troubleshooting Steps

1. **Verify IP Whitelisting**:
   - Check if your IP needs to be whitelisted in Salesforce
   - Setup → Security → Network Access

2. **Check User Permissions**:
   - Ensure your user has API access enabled
   - Setup → Users → Your User → Profile → Administrative Permissions → API Enabled

3. **Password Requirements**:
   - If you recently changed your password, you'll need a new security token
   - Security tokens are automatically reset when passwords change

4. **Account Lockout**:
   - Too many failed attempts can lock your account
   - Contact your Salesforce admin to unlock

### 5. Example .env Configuration

```bash
# Standard Salesforce (production)
SFDC_USERNAME=john.doe@company.com
SFDC_PASSWORD=MyPassword123
SFDC_SECURITY_TOKEN=AbCdEfGhIjKlMnOpQrStUv
SFDC_DOMAIN=login

# Salesforce Sandbox
SFDC_USERNAME=john.doe@company.com.sandbox
SFDC_PASSWORD=MyPassword123
SFDC_SECURITY_TOKEN=AbCdEfGhIjKlMnOpQrStUv
SFDC_DOMAIN=test

# Custom Domain
SFDC_USERNAME=john.doe@company.com
SFDC_PASSWORD=MyPassword123
SFDC_SECURITY_TOKEN=AbCdEfGhIjKlMnOpQrStUv
SFDC_DOMAIN=mycompany.my
```

### 6. Quick Test Script

Save this as `test_sfdc.py` and run it:

```python
import os
from dotenv import load_dotenv
from simple_salesforce import Salesforce

load_dotenv()

try:
    sf = Salesforce(
        username=os.getenv('SFDC_USERNAME'),
        password=os.getenv('SFDC_PASSWORD'),
        security_token=os.getenv('SFDC_SECURITY_TOKEN'),
        domain=os.getenv('SFDC_DOMAIN', 'login')
    )
    
    # Test query
    result = sf.query("SELECT Id, CaseNumber FROM Case LIMIT 1")
    print(f"✅ Connected successfully! Found {result['totalSize']} cases")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nPlease verify:")
    print("1. Username is correct")
    print("2. Password is correct") 
    print("3. Security token is current (reset if password changed)")
    print("4. Domain is correct (login, test, or custom domain prefix)")
```

### 7. Using Without Real SFDC Access

If you don't have valid SFDC credentials yet, you can:

1. **Use Mock Data**: Modify the SFDC client to return sample data
2. **Skip SFDC Steps**: Build index from provided sample data
3. **Request Demo Access**: Ask for a Salesforce Developer Edition (free)

To proceed without SFDC:
```bash
# Skip SFDC connection and use sample data
make build-index-sample --mock-data
```