BEGIN;

-- Create new comprehensive service role policies
CREATE POLICY "Service role has full access to API keys"
ON public.api_keys
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Service role has full access to credits"
ON public.credits
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

COMMIT;