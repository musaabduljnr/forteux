-- ==============================================================================
-- FORTEUX PRODUCTION SECURITY HARDENING & ADVISOR FIXES
-- ==============================================================================

-- 1. Fix mutable search_path on security definer functions
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = public, auth, pg_temp
AS $$
BEGIN
    INSERT INTO public.profiles (
        id,
        full_name,
        email,
        avatar_url,
        onboarding_completed,
        created_at,
        updated_at
    )
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', ''),
        NEW.email,
        NEW.raw_user_meta_data->>'avatar_url',
        FALSE,
        NOW(),
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        full_name = EXCLUDED.full_name,
        avatar_url = COALESCE(EXCLUDED.avatar_url, profiles.avatar_url),
        updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.current_tenant_id() 
RETURNS uuid 
LANGUAGE plpgsql 
STABLE 
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN (NULLIF(current_setting('request.jwt.claims', true)::json->>'tenant_id', '')::uuid);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.current_user_id() 
RETURNS uuid 
LANGUAGE plpgsql 
STABLE 
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN (NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

-- 2. Revoke public/anon/authenticated execution of internal helper functions from PostgREST RPC
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.current_tenant_id() FROM anon;
REVOKE EXECUTE ON FUNCTION public.current_user_id() FROM anon;

-- 3. Optimize RLS subquery performance (InitPlan optimization using (SELECT auth.uid()))
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own"
    ON public.profiles
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = id);

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own"
    ON public.profiles
    FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = id)
    WITH CHECK ((SELECT auth.uid()) = id);

DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
CREATE POLICY "profiles_insert_own"
    ON public.profiles
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = id);
