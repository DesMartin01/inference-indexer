-- Migration 003: Supabase Auth Integration
-- Links auth.users to api_users table via trigger
-- When a user signs up via Supabase Auth, automatically create their api_users row with generated API key

-- 1. Add Supabase Auth user ID column to api_users
ALTER TABLE api_users ADD COLUMN IF NOT EXISTS auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- 2. Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_api_users_auth_user_id ON api_users(auth_user_id);

-- 3. Function to generate random API key (matches existing format)
CREATE OR REPLACE FUNCTION generate_sit_api_key()
RETURNS TEXT AS $$
BEGIN
    RETURN 'sit_' || encode(gen_random_bytes(24), 'hex');
END;
$$ LANGUAGE plpgsql;

-- 4. Trigger function: auto-create api_users row when auth user is created
CREATE OR REPLACE FUNCTION handle_new_auth_user()
RETURNS TRIGGER AS $$
DECLARE
    new_api_key TEXT;
BEGIN
    new_api_key := generate_sit_api_key();
    
    INSERT INTO api_users (email, api_key, plan, auth_user_id)
    VALUES (NEW.email, new_api_key, 'free', NEW.id)
    ON CONFLICT (email) DO UPDATE 
    SET auth_user_id = NEW.id,
        api_key = COALESCE(api_users.api_key, new_api_key);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Drop existing trigger if any, then create
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user();

-- 6. RLS: Let users read their own api_users row
DROP POLICY IF EXISTS "Users can read own api data" ON api_users;
CREATE POLICY "Users can read own api data" ON api_users
    FOR SELECT USING (auth_user_id = auth.uid());

-- 7. Update the latest_prices view to include auth_user_id if needed
-- (not needed, latest_prices is about prices not users)
