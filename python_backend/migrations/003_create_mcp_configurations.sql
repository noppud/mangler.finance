-- MCP configurations table (user-scoped)
CREATE TABLE IF NOT EXISTS public.mcp_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,           -- Kinde user ID
    name TEXT NOT NULL,               -- User-friendly name (e.g., "My Google Drive")
    mcp_type TEXT NOT NULL DEFAULT 'stdio',  -- 'stdio' only for now
    command TEXT NOT NULL,            -- e.g., "npx", "python", "node", "/usr/local/bin/mcp-server"
    args JSONB NOT NULL,              -- e.g., ["@modelcontextprotocol/server-gdrive"]
    env JSONB DEFAULT '{}'::jsonb,   -- Environment variables (encrypted)
    enabled BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,  -- { description, icon, etc. }
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Enforce unique names per user
    UNIQUE(user_id, name)
);

-- Index for fast user lookups
CREATE INDEX mcp_configurations_user_id_enabled_idx
    ON public.mcp_configurations (user_id, enabled);

-- Function to enforce max 5 MCPs per user
CREATE OR REPLACE FUNCTION check_max_mcps_per_user()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM public.mcp_configurations WHERE user_id = NEW.user_id) >= 5 THEN
        RAISE EXCEPTION 'Maximum 5 MCP configurations allowed per user';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce the limit
CREATE TRIGGER enforce_max_mcps_per_user
    BEFORE INSERT ON public.mcp_configurations
    FOR EACH ROW
    EXECUTE FUNCTION check_max_mcps_per_user();

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_mcp_configurations_updated_at
    BEFORE UPDATE ON public.mcp_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
