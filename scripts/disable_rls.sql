-- Completely disable RLS for data import
-- Run this in Supabase SQL Editor

-- Disable RLS on all tables
ALTER TABLE repositories DISABLE ROW LEVEL SECURITY;
ALTER TABLE agents DISABLE ROW LEVEL SECURITY;
ALTER TABLE classifications DISABLE ROW LEVEL SECURITY;
ALTER TABLE tech_stacks DISABLE ROW LEVEL SECURITY;

-- Note: This will make all data publicly readable
-- For production use, you may want to re-enable RLS with proper policies after import