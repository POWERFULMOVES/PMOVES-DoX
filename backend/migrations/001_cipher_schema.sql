-- Enable pgvector extension if not already enabled (requires db admin)
-- create extension if not exists vector;

-- Table: cipher_memory
-- Stores long-term memory items (facts, preferences, skills, workflows)
create table if not exists cipher_memory (
    id uuid primary key default gen_random_uuid(),
    category text not null check (category in ('fact', 'preference', 'skill_learned', 'workflow', 'other')),
    content jsonb not null default '{}'::jsonb,
    context jsonb default '{}'::jsonb,
    -- embedding vector(1536), -- Uncomment if pgvector is enabled and embedding is desired
    created_at timestamptz default now()
);

-- Table: user_prefs
-- Stores user-specific settings and UI preferences
create table if not exists user_prefs (
    user_id uuid primary key, -- Maps to Supabase Auth user.id
    preferences jsonb not null default '{}'::jsonb,
    updated_at timestamptz default now()
);

-- Table: skills_registry
-- Catalog of available agent capabilities and workflows
create table if not exists skills_registry (
    id uuid primary key default gen_random_uuid(),
    name text unique not null,
    description text,
    parameters jsonb default '{}'::jsonb,
    workflow_def jsonb default '{}'::jsonb,
    enabled boolean default true,
    created_at timestamptz default now()
);

-- Indexes (Optional, for performance)
create index if not exists idx_cipher_memory_category on cipher_memory(category);
create index if not exists idx_cipher_memory_created_at on cipher_memory(created_at);
create index if not exists idx_skills_registry_name on skills_registry(name);
create index if not exists idx_user_prefs_updated_at on user_prefs(updated_at);

-- Row Level Security (RLS) Policies
-- Enable RLS on all tables
alter table cipher_memory enable row level security;
alter table user_prefs enable row level security;
alter table skills_registry enable row level security;

-- Policy: cipher_memory
-- Note: cipher_memory table needs a user_id column for proper ownership scoping
-- For now, we'll use a policy that allows all authenticated users to read/write
-- TODO: Add user_id column to cipher_memory and update policy to scope to auth.uid()
create policy "cipher_memory_authenticated_policy" on cipher_memory
    for all
    to authenticated
    using (true)
    with check (true);

-- Policy: user_prefs
create policy "user_prefs_own_policy" on user_prefs
    for all
    to authenticated
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- Policy: skills_registry (global read, admin write)
create policy "skills_registry_read_policy" on skills_registry
    for select
    to authenticated
    using (true);

create policy "skills_registry_write_policy" on skills_registry
    for insert, update, delete
    to authenticated
    using (auth.jwt()->>'role' = 'admin' or auth.uid() is null);

