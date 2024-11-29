# Authentication & Authorization System

## Overview
This is a FastAPI-based authentication system with Role-Based Access Control (RBAC) supporting user registration, login, token management, and role-based endpoint access.

## Prerequisites
- Docker

## Installation
- Run the Command
    ```bash
    docker-compose up
    ```

## System Roles
- **Admin (Role ID: 1)**: Full system access
- **Moderator (Role ID: 2)**: Moderate access
- **User (Role ID: 3)**: Basic access

## API Endpoints

### 1. User Registration
```bash
curl -X POST http://localhost:8000/register \
     -H "Content-Type: application/json" \
     -d '{
         "username": "newuser",
         "password": "securepassword123",
         "role": 3
     }'
```
- Registers a new user
- Requires unique username
- Validates role existence
- Hashes password before storage
- For role refer [Link](#System-Roles)

### 2. User Login
```bash
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/json" \
     -d '{
         "username": "newuser",
         "password": "securepassword123"
     }'
```
- Authenticates user
- Returns JWT token and active time
- Token required for subsequent authenticated requests

### 3. Token Refresh
```bash
curl -X POST http://localhost:8000/refresh/token \
     -H "Authorization: Bearer YOUR__TOKEN"
```
- Extends token's active time
- Requires valid authentication token

### 4. Logout (Current Session)
```bash
curl -X POST http://localhost:8000/logout \
     -H "Authorization: Bearer YOUR__TOKEN"
```
- Invalidates current session token

### 5. Logout (All Sessions)
```bash
curl -X POST http://localhost:8000/logout_all \
     -H "Authorization: Bearer YOUR__TOKEN"
```
- Invalidates all active tokens for the user

### 6. Role-Specific Endpoints

#### Admin Endpoint
```bash
curl -X GET http://localhost:8000/admin_path \
     -H "Authorization: Bearer YOUR__TOKEN"
```
- Accessible only by Admin role

#### Moderator Endpoint
```bash
curl -X GET http://localhost:8000/moderator_path \
     -H "Authorization: Bearer YOUR__TOKEN"
```
- Accessible only by Moderator role

#### User Endpoint
```bash
curl -X GET http://localhost:8000/user_path \
     -H "Authorization: Bearer YOUR__TOKEN"
```
- Accessible by User role

## Notes
- Ensure Redis is running for token management
- Initial roles are loaded from `fixture/roles.json`
- You can change the session timeout from `settings.py`