create table api_keys (
    key_id uuid primary key,
    user_id uuid references auth.users(id),
    created_at timestamp with time zone default now(),
    revoked_at timestamp with time zone
);
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

-- Add after table creation
create policy "Users can view their own API keys"
  on api_keys for select
  using (auth.uid() = user_id);

create policy "Users can create their own API keys"
  on api_keys for insert
  with check (auth.uid() = user_id);

create policy "Users can delete their own API keys"
  on api_keys for delete
  using (auth.uid() = user_id);
