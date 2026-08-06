# InferenceIndexer: Auth & API Key Management Spec

> Phase 2 of InferenceIndexer. Adds user authentication, API key management, and a dashboard. Goal: convert index awareness into free API users (Phase 2 of Authority-First Marketing strategy).

## Current State

**Already built (backend):**
- `api_users` table in Supabase (id, email, api_key, plan, created_at, last_accessed_at, request_count, rate_limit_per_day)
- `POST /v1/auth/signup?email=...` endpoint: creates user, returns API key
- Rate limiting: public 1k/day, free 10k/day, paid 50k/day, SSR 100k/day
- Bearer token auth on all data endpoints
- Login/Sign Up links in nav (currently dead `#login` / `#signup` anchors)

**Missing (what this spec covers):**
1. Frontend auth pages (login, signup)
2. Email verification
3. Dashboard (view/copy API key, see usage, docs)
4. Supabase Auth integration (or simpler: email + magic link / verification code)
5. API key display and management

---

## Architecture Decision: Supabase Auth vs Custom

### Option A: Supabase Auth (Recommended)

Supabase provides built-in auth with email verification, session management, and row-level security.

**Pros:**
- Email verification built in
- Session management (JWT cookies)
- RLS policies already partially set up on `api_users`
- No password storage to worry about
- Magic link or OTP (no passwords needed at all)
- Free tier: 50,000 monthly active users

**Cons:**
- Adds `@supabase/supabase-js` dependency to frontend
- Need to sync Supabase Auth user ID with `api_users` table
- Next.js 16 client/server component complexity

### Option B: Custom (Email + API Key Only)

Current `POST /v1/auth/signup?email=...` approach. No passwords, no sessions. User enters email, gets API key, uses it in API calls.

**Pros:**
- Dead simple. Already 80% built.
- No frontend auth library needed
- No session management
- API key IS the auth token

**Cons:**
- No email verification (anyone can sign up with any email)
- No way to recover a lost API key except email-based lookup (already implemented: same email returns same key)
- No session for dashboard (would need to store key in localStorage)
- No password protection for the dashboard

### Recommendation: Option A (Supabase Auth)

**Reasoning:** The marketing strategy targets enterprise credibility. An unverified email signup flow is not credible for a "price reporting agency" positioning. Supabase Auth gives email verification, proper sessions, and a foundation for the paid tier (Phase 3). The magic link flow (no passwords) is also the most developer-friendly UX.

**However:** If Des wants to ship fast (days, not weeks), Option B gets a working signup flow live in 1-2 days. Option A takes 3-5 days.

---

## Implementation Spec: Option A (Supabase Auth)

### 1. Database Changes

**Migration 003: Link Supabase Auth to api_users**

```sql
-- Add Supabase Auth user ID to api_users
ALTER TABLE api_users ADD COLUMN IF NOT EXISTS auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Create a trigger to auto-create an api_users row when a new auth user signs up
CREATE OR REPLACE FUNCTION handle_new_auth_user()
RETURNS TRIGGER AS $$
DECLARE
    new_api_key TEXT;
BEGIN
    -- Generate a random API key (same format as existing)
    new_api_key := 'sit_' || encode(gen_random_bytes(24), 'hex');
    
    INSERT INTO api_users (email, api_key, plan, auth_user_id)
    VALUES (NEW.email, new_api_key, 'free', NEW.id)
    ON CONFLICT (email) DO UPDATE SET auth_user_id = NEW.id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user();
```

**Why:** When a user signs up via Supabase Auth, a trigger automatically creates their `api_users` row with a generated API key. No manual signup endpoint needed.

### 2. Frontend Pages

#### 2a. Login Page (`/login`)
- Email input
- "Send magic link" button
- On submit: `supabase.auth.signInWithOtp({ email })`
- Show: "Check your email for a login link"
- Magic link redirects to `/dashboard`
- Also: "Don't have an account? Sign up" link to `/signup`

#### 2b. Signup Page (`/signup`)
- Email input
- "Create account" button
- On submit: `supabase.auth.signUp({ email })`
- Show: "Check your email to verify your account"
- Email contains verification link redirecting to `/dashboard`
- Also: "Already have an account? Login" link to `/login`

#### 2c. Dashboard Page (`/dashboard`)
- Protected route: redirect to `/login` if not authenticated
- Shows:
  - User's API key (masked by default, "Show" button to reveal, "Copy" button)
  - Plan: Free (with "Upgrade" CTA when paid tier exists)
  - Usage: requests today / daily limit
  - Quick start code snippet (curl example with their key)
  - Links to API docs
- API key regeneration button ("Generate new key" with confirmation)

#### 2d. Auth Callback Page (`/auth/callback`)
- Handles Supabase Auth redirect after magic link / verification
- Exchanges code for session
- Redirects to `/dashboard` on success, `/login` on failure

### 3. Frontend Architecture

**Supabase Client Setup:**
```
web/src/lib/supabase/
  client.ts    — Browser client (createBrowserClient)
  server.ts    — Server client (createServerClient, for SSR/dashboard)
  middleware.ts — Session refresh middleware
```

**Environment variables needed:**
```
NEXT_PUBLIC_SUPABASE_URL=https://xuisyromkbxopciiourz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[from Supabase dashboard]
```

**Middleware (`web/src/middleware.ts`):**
- Refreshes Supabase session on every request
- Protects `/dashboard` route (redirect to `/login` if no session)
- Does NOT protect public pages (homepage, model pages, methodology, about)

### 4. API Changes

**Deprecate `POST /v1/auth/signup`:**
- The Supabase Auth trigger handles user creation now
- Keep endpoint for backward compatibility but mark as deprecated
- Frontend signup goes through Supabase Auth, not the API

**New endpoint: `GET /v1/auth/me`**
- Requires Bearer token (API key)
- Returns: email, plan, request_count, rate_limit_per_day, daily_requests_used
- Used by the dashboard to show usage stats

**New endpoint: `POST /v1/auth/regenerate-key`**
- Requires Bearer token (current API key)
- Generates new key, updates `api_users` table
- Returns new key
- Invalidates old key immediately

### 5. Nav Bar Updates

**Current state:** `Login` and `Sign Up` are dead `#login` / `#signup` anchors.

**New state:**
- If not logged in: `Login` links to `/login`, `Sign Up` links to `/signup`
- If logged in: Show user email + dropdown with `Dashboard` and `Sign Out`

### 6. Security Considerations

- **API keys in the browser:** The dashboard shows the API key. This is standard practice (OpenAI, Anthropic, etc. all do this). Key is only shown after authenticated session.
- **Rate limit enforcement:** Already in place. The `check_rate_limit()` function checks the `api_users` table.
- **RLS on api_users:** Already enabled. The trigger uses `SECURITY DEFINER` to insert rows.
- **Magic link security:** Supabase handles token expiration, single-use, and rate limiting on auth attempts.
- **No passwords:** Magic link / OTP flow means no password storage, no password reset flows, no bcrypt.

### 7. User Flow

```
1. User visits inferenceindexer.ai
2. Clicks "Sign Up" in nav
3. Enters email on /signup
4. Receives verification email from Supabase
5. Clicks link in email → redirected to /auth/callback → /dashboard
6. Dashboard shows their API key: "sit_a1b2c3d4e5f6..."
7. User copies key, uses it in API calls
8. Returns to dashboard anytime to view key, check usage, regenerate
```

### 8. Phase 3 Prep (Paid Tier)

This design sets up for Phase 3 (paid API tier):
- `plan` column already exists in `api_users` (currently `free` or `paid`)
- Rate limits already tiered: free 10k/day, paid 50k/day
- Dashboard has "Upgrade" CTA placeholder
- Payment integration (Stripe) can be added later without restructuring auth
- Paid plan just needs: Stripe checkout → webhook → UPDATE api_users SET plan = 'paid' WHERE email = ...

---

## Build Sequence

| Step | What | Time | Dependency |
|------|------|------|------------|
| 1 | Get Supabase anon key from dashboard | 5 min | None |
| 2 | Run migration 003 (auth trigger) | 10 min | Supabase dashboard |
| 3 | Create Supabase client files (client.ts, server.ts, middleware.ts) | 30 min | Step 1 |
| 4 | Create `/signup` page | 1 hr | Step 3 |
| 5 | Create `/login` page | 1 hr | Step 3 |
| 6 | Create `/auth/callback` route | 30 min | Step 3 |
| 7 | Create `/dashboard` page | 2 hrs | Steps 3-6 |
| 8 | Update nav bar (Login/Sign Up links + auth state) | 30 min | Step 3 |
| 9 | Add `GET /v1/auth/me` endpoint to api.py | 30 min | None |
| 10 | Add `POST /v1/auth/regenerate-key` endpoint | 30 min | None |
| 11 | Wire dashboard to API (fetch usage, show key) | 1 hr | Steps 7, 9 |
| 12 | Test full flow: signup → email → dashboard → API call | 1 hr | All |
| 13 | Deploy and verify live | 30 min | Step 12 |

**Total estimate: 8-10 hours of build time.**

---

## Open Questions for Des

1. **Magic link vs password:** Magic link (no password, email only) is simpler and more secure. OK to go with that? Or do you want password-based auth?
2. **Email sender:** Supabase sends from their default domain. For branding, we can configure a custom SMTP (e.g., notifications@inferenceindexer.ai). Needed now or can wait?
3. **Dashboard scope:** The spec above is minimal (API key + usage). Do you want anything else on the dashboard? (Saved models, price alerts, API call logs?)
4. **Paid tier timing:** The marketing strategy says Phase 3 (Months 3-12). Do you want the "Upgrade" button to be a no-op placeholder for now, or should we start thinking about Stripe integration in this phase?
5. **Rate limit display:** Should the dashboard show real-time usage counts, or is the daily limit number enough?
6. **API key format:** Currently `sit_` prefix + random hex. Want to keep this, or change to something more brand-aligned?
7. **Option A vs B:** Supabase Auth (3-5 days, email verified, enterprise-credible) vs custom email signup (1-2 days, no verification, faster to ship). Which do you prefer?
