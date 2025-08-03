# Google Login Testing Guide

This guide explains how to test Google OAuth login functionality in the Skipping Stones application.

## Overview

Google OAuth testing is complex because it requires:
1. Real Google OAuth credentials
2. HTTPS in production (Google requirement)
3. Proper redirect URI configuration
4. Token exchange and verification

## Test Categories

### 1. **Configuration Tests** (No Credentials Required)
- ✅ Check if Google OAuth environment variables are set
- ✅ Verify login endpoint redirects to Google OAuth
- ✅ Test callback endpoint behavior without authorization code
- ✅ Validate OAuth URL structure

### 2. **Authentication Tests** (No Credentials Required)
- ✅ Test that protected endpoints require authentication
- ✅ Verify logout functionality
- ✅ Test switch account functionality

### 3. **Mock Tests** (No Credentials Required)
- ✅ Mock Google OAuth token exchange
- ✅ Mock user info retrieval
- ✅ Test JWT token verification

### 4. **Integration Tests** (Requires Real Credentials)
- ⚠️ Full OAuth flow testing
- ⚠️ Real token exchange
- ⚠️ User session management

## Running Tests

### Basic Tests (No Setup Required)
```bash
# Run all tests including Google login tests
python3 run_tests.py

# Run only Google login tests
python3 tests/test_google_login.py
```

### With Google OAuth Credentials
```bash
# Set environment variables
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/callback"

# Run tests
python3 tests/test_google_login.py
```

## Setting Up Google OAuth for Testing

### 1. Create Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Configure:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:5000/callback`
   - Authorized JavaScript origins: `http://localhost:5000`

### 2. Set Environment Variables
```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/callback"
```

### 3. Test the Full Flow
```bash
# Start the server
python3 app.py

# In another terminal, run tests
python3 tests/test_google_login.py
```

## Test Results Interpretation

### ✅ **Passing Tests**
- **Login Endpoint**: Redirects to Google OAuth correctly
- **OAuth URL Structure**: Contains all required parameters
- **Authentication Required**: Protected endpoints return 401
- **Switch Account**: Redirects to login page
- **Mock OAuth Flow**: Simulated token exchange works

### ⚠️ **Skipped Tests** (When Credentials Not Set)
- **Google OAuth Configuration**: Environment variables not set
- **Full OAuth Flow**: Requires real credentials

### ❌ **Failing Tests** (Need Investigation)
- **Callback Endpoint**: Should redirect or show error page
- **Token Verification**: JWT verification issues

## Manual Testing

### 1. **Test Login Flow**
```bash
# Start server
python3 app.py

# Open browser
open http://localhost:5000

# Click "Login" button
# Should redirect to Google OAuth
# Complete OAuth flow
# Should return to game with user logged in
```

### 2. **Test Logout Flow**
```bash
# After logging in, click "Logout"
# Should clear session and show fresh game
# User should appear as not logged in
```

### 3. **Test Switch Account**
```bash
# While logged in, click "Switch Account"
# Should redirect to login page
# Should allow selecting different Google account
```

## Troubleshooting

### Common Issues

1. **"Invalid redirect_uri"**
   - Check that redirect URI in Google Console matches exactly
   - Must be `http://localhost:5000/callback` for local testing

2. **"Client ID not found"**
   - Verify GOOGLE_CLIENT_ID is set correctly
   - Check that the client ID exists in Google Console

3. **"Invalid token"**
   - Check that GOOGLE_CLIENT_SECRET is correct
   - Verify JWT verification is working

4. **"HTTPS required"**
   - Google requires HTTPS in production
   - Local testing can use HTTP
   - Use ngrok or similar for HTTPS testing

### Debug Commands

```bash
# Check environment variables
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# Test login endpoint
curl -v http://localhost:5000/login

# Test callback endpoint
curl -v http://localhost:5000/callback

# Check auth status
curl http://localhost:5000/api/auth/status
```

## Security Considerations

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Test with mock data** when possible
4. **Validate tokens** on server side
5. **Use HTTPS** in production

## Future Improvements

1. **Add integration tests** with real OAuth flow
2. **Mock Google APIs** for consistent testing
3. **Add test coverage** for edge cases
4. **Create test fixtures** for common scenarios
5. **Add performance tests** for OAuth flow 