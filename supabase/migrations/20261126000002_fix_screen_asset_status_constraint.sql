-- ==============================================================================
-- FIX ck_screen_asset_status CHECK CONSTRAINT TO MATCH ORM MODEL
-- ==============================================================================
-- Adds 'uploaded_verified' to screen_assets.status check constraint so
-- POST /projects/{id}/assets/{asset_id}/complete can mark verified uploads.
-- ==============================================================================

ALTER TABLE public.screen_assets
    DROP CONSTRAINT IF EXISTS ck_screen_asset_status;

ALTER TABLE public.screen_assets
    ADD CONSTRAINT ck_screen_asset_status
    CHECK (status IN ('pending_upload', 'uploaded_unverified', 'uploaded_verified', 'deleting', 'deleted'));
