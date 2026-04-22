-- Add phone_no and platform_role columns to profiles table
-- Run in Supabase SQL Editor

ALTER TABLE fieldops.profiles
ADD COLUMN IF NOT EXISTS phone_no TEXT,
ADD COLUMN IF NOT EXISTS platform_role TEXT;
