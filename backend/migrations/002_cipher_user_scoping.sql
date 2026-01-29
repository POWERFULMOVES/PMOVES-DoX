-- Migration: Add user_id column to cipher_memory and update RLS policy
-- This migration adds proper user scoping to the cipher_memory table
-- so each user can only access their own memories.

-- Step 1: Add user_id column to cipher_memory
-- Using uuid type to match Supabase Auth user.id
alter table cipher_memory add column if not exists user_id uuid;

-- Step 2: Create index for efficient user-based queries
create index if not exists idx_cipher_memory_user_id on cipher_memory(user_id);

-- Step 3: Drop the old permissive policy
drop policy if exists "cipher_memory_authenticated_policy" on cipher_memory;

-- Step 4: Create new user-scoped RLS policy
-- Users can only read/write their own memories
create policy "cipher_memory_user_owned_policy" on cipher_memory
    for all
    to authenticated
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- Step 5: Create policy for service role to bypass RLS
-- This allows backend services with service_role key to access all memories
create policy "cipher_memory_service_role_policy" on cipher_memory
    for all
    to service_role
    using (true)
    with check (true);

-- Note: Existing records without user_id will not be accessible via the user policy
-- You may want to run a data migration to assign user_ids to existing records
-- or create an additional policy for anonymous/unassigned records if needed.
