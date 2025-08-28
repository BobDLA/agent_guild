-- Alternative: Create very permissive RLS policies
-- Run this in Supabase SQL Editor

-- Drop existing policies
DROP POLICY IF EXISTS "Public read access" ON repositories;
DROP POLICY IF EXISTS "Public read access" ON agents;
DROP POLICY IF EXISTS "Public read access" ON classifications;
DROP POLICY IF EXISTS "Public read access" ON tech_stacks;
DROP POLICY IF EXISTS "Service role all access" ON repositories;
DROP POLICY IF EXISTS "Service role all access" ON agents;
DROP POLICY IF EXISTS "Service role all access" ON classifications;
DROP POLICY IF EXISTS "Service role all access" ON tech_stacks;

-- Create completely open policies for development
CREATE POLICY "Allow all access" ON repositories FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON agents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON classifications FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON tech_stacks FOR ALL USING (true) WITH CHECK (true);