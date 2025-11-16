-- MCP tool call rate limiting (100 calls/hour per MCP)
CREATE TABLE IF NOT EXISTS public.mcp_tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mcp_config_id UUID NOT NULL REFERENCES public.mcp_configurations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    called_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER
);

-- Index for rate limit queries (last hour)
CREATE INDEX mcp_tool_calls_rate_limit_idx
    ON public.mcp_tool_calls (mcp_config_id, called_at DESC);

-- Index for user analytics
CREATE INDEX mcp_tool_calls_user_idx
    ON public.mcp_tool_calls (user_id, called_at DESC);

-- Auto-cleanup old records (older than 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_mcp_tool_calls()
RETURNS void AS $$
BEGIN
    DELETE FROM public.mcp_tool_calls
    WHERE called_at < now() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
