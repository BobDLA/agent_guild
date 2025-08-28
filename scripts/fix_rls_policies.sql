-- Fix RLS policies to allow service_role inserts
-- Run this in Supabase SQL Editor after the initial schema

-- Drop existing service role policies
DROP POLICY IF EXISTS "Service role all access" ON repositories;
DROP POLICY IF EXISTS "Service role all access" ON agents;
DROP POLICY IF EXISTS "Service role all access" ON classifications;
DROP POLICY IF EXISTS "Service role all access" ON tech_stacks;

-- Create new service role policies with broader access
CREATE POLICY "Service role all access" ON repositories FOR ALL USING (auth.role() = 'service_role' OR auth.role() IS NULL) WITH CHECK (auth.role() = 'service_role' OR auth.role() IS NULL);
CREATE POLICY "Service role all access" ON agents FOR ALL USING (auth.role() = 'service_role' OR auth.role() IS NULL) WITH CHECK (auth.role() = 'service_role' OR auth.role() IS NULL);
CREATE POLICY "Service role all access" ON classifications FOR ALL USING (auth.role() = 'service_role' OR auth.role() IS NULL) WITH CHECK (auth.role() = 'service_role' OR auth.role() IS NULL);
CREATE POLICY "Service role all access" ON tech_stacks FOR ALL USING (auth.role() = 'service_role' OR auth.role() IS NULL) WITH CHECK (auth.role() = 'service_role' OR auth.role() IS NULL);

-- Alternative: Allow inserts for authenticated users (simpler approach)
-- Uncomment the lines below if the above doesn't work
/*
CREATE POLICY "Enable insert for authenticated users" ON repositories FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Enable insert for authenticated users" ON agents FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Enable insert for authenticated users" ON classifications FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Enable insert for authenticated users" ON tech_stacks FOR INSERT WITH CHECK (auth.role() = 'authenticated');
*/