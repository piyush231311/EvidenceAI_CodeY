# Security & Threat Model

Evidence AI is a victim-first digital evidence platform built for individuals facing harassment, stalking, and abuse. In many domestic violence and stalking situations, the abuser shares physical devices, monitors local network traffic, or has access to email and cloud accounts.

Our security and privacy model is engineered specifically around these threats.

---

## What Is Protected

### 1. Memory-Hard Password Hashing (Argon2id)
- Passwords are never stored in plaintext or logged.
- Passwords are saved as Argon2id hashes with `time_cost=2`, `memory_cost=102400` (100 MB RAM), and `parallelism=8`, making GPU-accelerated brute-force attacks computationally infeasible.
- Re-hashing is automatically triggered on login if algorithmic cost parameters are upgraded.
- Top common passwords (>2,000 common and sequenced passwords) are blocked on registration.

### 2. Protected Session Cookies
- Sessions use JSON Web Tokens (JWT) stored exclusively in `httpOnly`, `SameSite`, and `Secure` cookies.
- JavaScript cannot read session tokens, eliminating token extraction via XSS.
- Tokens utilize sliding expiration with automatic renewal while active.
- Global sign-out increments a `token_version` on the user record, instantly invalidating all tokens issued to other browsers or devices.

### 3. CSRF & Request Forgery Defense
- Every state-changing API request (`POST`, `PUT`, `PATCH`, `DELETE`) enforces the `X-Requested-With: evidence-ai` header via strict backend middleware.
- Requests without this header are rejected with `403 Forbidden`, neutralizing cross-site request forgery attacks.

### 4. Strict Ownership Isolation & Zero Leakage
- Every case, evidence item, and audit log record is bound to the owner's `user_id`.
- If User B attempts to access, query, download, or upload to User A's case, the server returns an identical `404 Not Found` (never `403 Forbidden`). An unauthorized user cannot even infer whether a case or evidence ID exists.
- Case and evidence listings strictly filter by `user_id == current_user.id`.

### 5. Offline Recovery Codes
- At registration, users receive 8 single-use recovery codes with 60 bits of cryptographic entropy (formatted as `XXXX-XXXX-XXXX`).
- Recovery codes are stored as SHA-256 hashes; plaintext codes are displayed only once and never stored on the server.
- Using a recovery code resets the password, generates a fresh batch of 8 codes, and invalidates all existing sessions.

### 6. Rate Limiting & Account Lockout
- Authentication routes (`/api/auth/login`, `/api/auth/register`, `/api/auth/recover`) are rate-limited per IP.
- Five consecutive failed login attempts trigger an automatic 15-minute account lockout (`429 Too Many Requests`).
- Unknown username attempts execute a constant-time dummy password verification to neutralize timing attacks.

### 7. Victim Safety Features
- **Quick Exit**: The Quick Exit button and double-`Escape` shortcut immediately trigger a `POST /api/auth/logout` call with `keepalive: true` to invalidate the server session before redirecting to a neutral website.
- **Inactivity Auto-Logout**: After 14 minutes of inactivity, a 60-second warning modal is displayed. At 15 minutes, the user is signed out and redirected to `/login`.
- **Cross-Tab Sync**: Logging out in one tab immediately notifies all other open tabs via `BroadcastChannel`, closing active sessions.

---

## What Is NOT Protected (Threat Model Transparency)

To maintain realistic expectations for victims and advocates, the following limitations should be understood:

1. **Local Filesystem Access**:
   Evidence files in `./storage/originals/` are stored on the local disk. If an attacker possesses local administrative rights or physical root access to the computer, they may read files directly from the filesystem. **We strongly recommend enabling full-disk encryption (such as Windows BitLocker or macOS FileVault)**.

2. **No Email Password Reset (By Design)**:
   We intentionally do NOT offer password recovery via email or SMS. Abusers frequently monitor, compromise, or access the victim's email and phone, and password reset notifications could trigger retaliation.

3. **Loss of Recovery Codes**:
   Because Evidence AI is self-hosted with zero backdoors, **recovery codes are the only way to recover an account if a password is forgotten**. If both the password and recovery codes are lost, the account data cannot be decrypted or restored.

4. **Hardware Keyloggers & Active Malware**:
   If an abuser has installed kernel-level keyloggers or screen-recording spyware on the device prior to the user accessing Evidence AI, keystrokes may be captured at the operating system level.
