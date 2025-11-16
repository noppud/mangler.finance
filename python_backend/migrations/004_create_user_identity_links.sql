-- User identity linking table (Google ↔ Kinde)
CREATE TABLE IF NOT EXISTS public.user_identity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kinde_user_id TEXT NOT NULL UNIQUE,
    google_email TEXT NOT NULL UNIQUE,
    google_sub TEXT,                    -- Google subject ID (optional)
    linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Ensure bidirectional uniqueness
    UNIQUE(kinde_user_id, google_email)
);

-- Indexes for both directions of lookup
CREATE INDEX user_identity_links_kinde_idx
    ON public.user_identity_links (kinde_user_id);

CREATE INDEX user_identity_links_google_idx
    ON public.user_identity_links (google_email);
