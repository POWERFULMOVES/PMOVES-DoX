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
create index if not exists idx_skills_registry_name on skills_registry(name);
