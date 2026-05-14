# Authentication Persistence Test Guide

## Test Steps:

1. **Start the app in debug mode** to see console logs
2. **Login with your credentials** (rushiraj@datagrid.co.in/admin123)
3. **Close the app completely** (not just minimize - force close)
4. **Reopen the app** and check what happens

## Expected Debug Logs:

### During Login:
```
AuthProvider: Starting login for rushiraj@datagrid.co.in
AuthProvider: Login successful, token: eyJ0eXAiOiJKV1QiLCJ...
ApiClient: Saved token: eyJ0eXAiOiJKV1QiLCJ...
AuthProvider: Saved login data
AuthProvider: Updated state to logged in
```

### During App Restart (Splash Screen):
```
AuthProvider: Starting auth status check
ApiClient: Retrieved token: eyJ0eXAiOiJKV1QiLCJ...
AuthProvider: isLoggedIn = true
ApiClient: Retrieved user data: Rushiraj Patel
AuthProvider: Retrieved user = Rushiraj Patel
AuthProvider: Set logged in state with user
Splash: Auth state - isLoading: false, isLoggedIn: true, user: Rushiraj Patel
```

## If Authentication Persistence is NOT Working:

You might see:
```
AuthProvider: Starting auth status check
ApiClient: Retrieved token: null
AuthProvider: isLoggedIn = false
AuthProvider: No valid token, setting logged out state
Splash: Auth state - isLoading: false, isLoggedIn: false, user: null
```

## Common Issues:

1. **Token not being saved**: Check if "ApiClient: Saved token" appears during login
2. **Token not being retrieved**: Check if "ApiClient: Retrieved token: null" appears on restart
3. **User data missing**: Check if user data is being saved and retrieved properly

## How to Run:

```bash
# Run in debug mode to see logs
flutter run --debug

# Or if using VS Code, run in debug mode and check the Debug Console
``` 