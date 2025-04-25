-- For api_keys table
ALTER TABLE public.api_keys
DROP CONSTRAINT api_keys_user_id_fkey,
ADD CONSTRAINT api_keys_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- For credit_transactions table
ALTER TABLE public.credit_transactions
DROP CONSTRAINT credit_transactions_user_id_fkey,
ADD CONSTRAINT credit_transactions_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- For credits table
ALTER TABLE public.credits
DROP CONSTRAINT credits_user_id_fkey,
ADD CONSTRAINT credits_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;