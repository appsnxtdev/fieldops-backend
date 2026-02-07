-- Run in Supabase SQL Editor. Profiles table for users module (fieldops schema).
CREATE TABLE IF NOT EXISTS fieldops.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_profiles_id ON fieldops.profiles(id);

ALTER TABLE fieldops.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
    ON fieldops.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON fieldops.profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON fieldops.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);
