-- Enable Row Level Security
alter table auth.users enable row level security;

-- Credits table
create table credits (
  user_id uuid references auth.users(id),
  is_guest boolean,
  balance integer not null default 0,
  last_free_credit_update timestamp with time zone,
  primary key (user_id)
);
ALTER TABLE public.credits ENABLE ROW LEVEL SECURITY;

-- Credit transactions table
create table credit_transactions (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references auth.users(id),
  amount integer not null,
  operation_type text not null,
  created_at timestamp with time zone default now()
);
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
create policy "Users can view their own credits"
  on credits for select
  using (auth.uid() = user_id);

create policy "System can modify credits"
  on credits for all
  using (auth.role() = 'service_role');

-- Function to add credits
create or replace function add_credits(
  p_user_id uuid,
  amount integer
) returns void
language plpgsql security definer as $$
begin
  insert into credits (user_id, balance, last_free_credit_update)
  values (p_user_id, amount, now())
  on conflict (user_id) do update
  set 
    balance = credits.balance + amount,
    last_free_credit_update = now();

  insert into credit_transactions (
    user_id,
    amount,
    operation_type
  ) values (
    p_user_id,
    amount,
    'addition'
  );
end;
$$;

-- Function to deduct credits
create or replace function public.deduct_credits(
  p_user_id uuid,
  amount integer,
  operation text
) returns boolean
language plpgsql security invoker set search_path = 'public' as $$
declare
  current_balance integer;
begin
  select balance into current_balance
  from credits
  where credits.user_id = p_user_id
  for update;
  
  if current_balance >= amount then
    update credits 
    set balance = balance - amount
    where credits.user_id = p_user_id;
    
    insert into credit_transactions (
      user_id,
      amount,
      operation_type
    ) values (
      p_user_id,
      -amount,
      operation
    );
    
    return true;
  end if;
  
  return false;
end;
$$;

