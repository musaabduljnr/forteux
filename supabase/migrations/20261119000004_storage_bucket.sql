-- ==============================================================================
-- FORTEUX STORAGE BUCKET & RLS POLICIES
-- ==============================================================================

-- 1. Create the private bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'forteux-private-assets',
    'forteux-private-assets',
    false,
    26214400, -- 25MB
    ARRAY['image/png', 'image/jpeg', 'image/webp', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 26214400,
    allowed_mime_types = ARRAY['image/png', 'image/jpeg', 'image/webp', 'application/pdf'];

-- 2. Storage RLS Policies
-- Allow authenticated users to view objects in their tenant/user folder
DROP POLICY IF EXISTS "Tenant asset read" ON storage.objects;
CREATE POLICY "Tenant asset read"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'forteux-private-assets' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Allow authenticated users to upload objects to their tenant/user folder
DROP POLICY IF EXISTS "Tenant asset insert" ON storage.objects;
CREATE POLICY "Tenant asset insert"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'forteux-private-assets' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Allow authenticated users to update objects in their tenant/user folder
DROP POLICY IF EXISTS "Tenant asset update" ON storage.objects;
CREATE POLICY "Tenant asset update"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'forteux-private-assets' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Allow authenticated users to delete objects in their tenant/user folder
DROP POLICY IF EXISTS "Tenant asset delete" ON storage.objects;
CREATE POLICY "Tenant asset delete"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'forteux-private-assets' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Service role bypass policy for FastAPI backend
DROP POLICY IF EXISTS "Service role storage bypass" ON storage.objects;
CREATE POLICY "Service role storage bypass"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'forteux-private-assets')
WITH CHECK (bucket_id = 'forteux-private-assets');
