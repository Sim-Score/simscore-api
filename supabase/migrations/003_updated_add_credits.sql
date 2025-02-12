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


