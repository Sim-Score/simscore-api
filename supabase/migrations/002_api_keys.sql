create table api_keys (
    key_id uuid primary key,
    user_id uuid references auth.users(id),
    created_at timestamp with time zone default now(),
    revoked_at timestamp with time zone
);
