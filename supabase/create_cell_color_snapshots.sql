-- * Create table to snapshot cell background colors for targeted ranges.
create table if not exists public.cell_color_snapshots (
    id uuid primary key default gen_random_uuid(),
    snapshot_batch_id uuid not null,
    spreadsheet_id text not null,
    gid integer,
    cell text not null,
    red double precision not null,
    green double precision not null,
    blue double precision not null,
    created_at timestamptz not null default now()
);

-- * Ensure quick lookup for a specific sheet + batch.
create index if not exists idx_cell_color_snapshots_sheet_batch
    on public.cell_color_snapshots (spreadsheet_id, gid, snapshot_batch_id);

