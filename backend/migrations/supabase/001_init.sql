create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
create extension if not exists "vector";

create table if not exists artifacts (
  id text primary key,
  filename text not null,
  filepath text not null,
  filetype text not null,
  report_week text,
  status text,
  created_at timestamptz default now()
);

create table if not exists documents (
  id text primary key,
  path text not null,
  type text not null,
  title text,
  source text,
  created_at text
);

create table if not exists document_sections (
  id text primary key,
  document_id text references documents(id) on delete cascade,
  "order" int not null,
  text text not null,
  page int,
  bbox_json jsonb
);

create table if not exists document_tables (
  id text primary key,
  document_id text references documents(id) on delete cascade,
  "order" int not null,
  json jsonb not null
);

create table if not exists api_endpoints (
  id text primary key,
  document_id text references documents(id) on delete cascade,
  name text,
  method text not null,
  path text not null,
  summary text,
  tags jsonb,
  params_json jsonb,
  responses_json jsonb
);

create table if not exists log_entries (
  id text primary key,
  document_id text references documents(id) on delete cascade,
  ts text,
  level text,
  code text,
  component text,
  message text,
  attrs jsonb
);

create index if not exists idx_log_entries_code on log_entries(code);
create index if not exists idx_log_entries_ts on log_entries(ts);

create table if not exists tags (
  id text primary key,
  document_id text references documents(id) on delete cascade,
  tag text not null,
  score double precision,
  source_ptr text,
  hrm_steps int
);

create index if not exists idx_tags_doc on tags(document_id);
create index if not exists idx_tags_tag on tags(tag);

create table if not exists facts (
  id text primary key,
  artifact_id text references artifacts(id) on delete cascade,
  report_week text,
  entity text,
  metrics jsonb not null default '{}'::jsonb
);

create table if not exists evidence (
  id text primary key,
  artifact_id text references artifacts(id) on delete cascade,
  locator text,
  preview text,
  content_type text,
  coordinates jsonb,
  full_data jsonb
);

create table if not exists tag_prompts (
  id text primary key,
  document_id text references documents(id) on delete cascade,
  prompt_text text not null,
  examples jsonb,
  created_at text,
  author text
);

create table if not exists search_chunks (
  id text primary key,
  document_id text,
  source_type text,
  chunk_index int,
  text text,
  meta jsonb,
  embedding vector(384),
  created_at timestamptz default now()
);

create index if not exists idx_search_chunks_document on search_chunks(document_id);
create index if not exists idx_search_chunks_embedding on search_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
