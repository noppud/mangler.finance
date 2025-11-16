<script lang="ts">
  import { onMount } from 'svelte';
  import type { MCPConfiguration, MCPConfigurationList } from '$lib/types/mcp';
  import AddMCPDialog from '$lib/components/AddMCPDialog.svelte';
  import { goto } from '$app/navigation';

  let configurations: MCPConfiguration[] = [];
  let loading = true;
  let showAddDialog = false;
  let error: string | null = null;
  let maxAllowed = 5;

  onMount(async () => {
    await loadConfigurations();
  });

  async function loadConfigurations() {
    loading = true;
    error = null;
    try {
      const response = await fetch('/api/mcp/configurations', {
        credentials: 'include'
      });

      if (response.status === 401) {
        // Not authenticated, redirect to login
        goto('/login');
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to load configurations');
      }

      const data: MCPConfigurationList = await response.json();
      configurations = data.configurations;
      maxAllowed = data.max_allowed;
    } catch (err) {
      console.error('Failed to load MCP configurations:', err);
      error = 'Failed to load MCP configurations. Please try again.';
    } finally {
      loading = false;
    }
  }

  async function toggleMCP(id: string, enabled: boolean) {
    try {
      const response = await fetch(`/api/mcp/configurations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ enabled: !enabled })
      });

      if (!response.ok) {
        throw new Error('Failed to toggle MCP');
      }

      await loadConfigurations();
    } catch (err) {
      console.error('Failed to toggle MCP:', err);
      error = 'Failed to toggle MCP. Please try again.';
    }
  }

  async function deleteMCP(id: string, name: string) {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;

    try {
      const response = await fetch(`/api/mcp/configurations/${id}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to delete MCP');
      }

      await loadConfigurations();
    } catch (err) {
      console.error('Failed to delete MCP:', err);
      error = 'Failed to delete MCP. Please try again.';
    }
  }

  function handleAddComplete() {
    showAddDialog = false;
    loadConfigurations();
  }
</script>

<div class="mcp-container">
  <header class="mcp-header">
    <h1 class="mcp-title">MCP Configurations</h1>
    <p class="mcp-subtitle">
      Extend your AI assistant with Model Context Protocol servers
    </p>
  </header>

  {#if error}
    <div class="error-banner">
      {error}
    </div>
  {/if}

  <div class="mcp-controls">
    <div class="mcp-counter">
      {configurations.length} of {maxAllowed} configurations
    </div>
    <button
      on:click={() => showAddDialog = true}
      disabled={configurations.length >= maxAllowed}
      class="mcp-add-button"
    >
      Add MCP Server
    </button>
  </div>

  {#if loading}
    <div class="loading-container">
      <div class="spinner"></div>
    </div>
  {:else if configurations.length === 0}
    <div class="empty-state">
      <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
      </svg>
      <h3 class="empty-state-title">No MCP servers configured</h3>
      <p class="empty-state-text">Add your first MCP to extend your agent's capabilities!</p>
      <button
        on:click={() => showAddDialog = true}
        class="mcp-add-button"
      >
        Add Your First MCP
      </button>
    </div>
  {:else}
    <div class="config-grid">
      {#each configurations as config}
        <div class="config-card">
          <div class="config-header">
            <div>
              <h3 class="config-name">{config.name}</h3>
              <span class="config-status {config.enabled ? 'active' : 'disabled'}">
                {config.enabled ? 'Active' : 'Disabled'}
              </span>
            </div>
            <label class="toggle-switch">
              <input
                type="checkbox"
                checked={config.enabled}
                on:change={() => toggleMCP(config.id, config.enabled)}
              />
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="config-details">
            <div class="config-detail">
              <strong>Command:</strong> {config.command}
            </div>
            <div class="config-detail">
              <strong>Args:</strong>
              <code>{config.args.join(' ')}</code>
            </div>
            {#if Object.keys(config.env || {}).length > 0}
              <div class="config-detail">
                <strong>Environment:</strong> {Object.keys(config.env).length} variables
              </div>
            {/if}
          </div>

          <div class="config-actions">
            <button
              on:click={() => deleteMCP(config.id, config.name)}
              class="delete-button"
            >
              Delete
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if showAddDialog}
    <AddMCPDialog
      on:close={() => showAddDialog = false}
      on:added={handleAddComplete}
    />
  {/if}
</div>

<style>
  .mcp-container {
    max-width: 1100px;
    margin: 0 auto;
  }

  .mcp-header {
    margin-bottom: 3rem;
  }

  .mcp-title {
    font-size: 2.5rem;
    font-weight: 800;
    color: #bffcd8;
    margin-bottom: 0.5rem;
    letter-spacing: -0.02em;
  }

  .mcp-subtitle {
    color: #9eb7ae;
    font-size: 1.1rem;
  }

  .error-banner {
    background: rgba(220, 38, 38, 0.1);
    border: 1px solid rgba(220, 38, 38, 0.3);
    color: #fca5a5;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .mcp-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .mcp-counter {
    color: #9eb7ae;
    font-size: 0.9rem;
  }

  .mcp-add-button {
    padding: 0.625rem 1.5rem;
    background: linear-gradient(135deg, rgba(48, 136, 95, 0.95), rgba(92, 221, 153, 0.95));
    color: #03140d;
    font-weight: 600;
    border-radius: 0.5rem;
    border: 1px solid rgba(84, 187, 130, 0.75);
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(58, 201, 136, 0.2);
  }

  .mcp-add-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(92, 221, 153, 0.3);
  }

  .mcp-add-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 16rem;
  }

  .spinner {
    width: 3rem;
    height: 3rem;
    border: 3px solid rgba(92, 221, 153, 0.2);
    border-top-color: #5cdd99;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    background: rgba(94, 115, 110, 0.1);
    border: 1px solid rgba(94, 115, 110, 0.2);
    border-radius: 0.75rem;
  }

  .empty-state-icon {
    width: 4rem;
    height: 4rem;
    margin: 0 auto 1.5rem;
    color: #5e736e;
  }

  .empty-state-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #bffcd8;
    margin-bottom: 0.5rem;
  }

  .empty-state-text {
    color: #9eb7ae;
    margin-bottom: 1.5rem;
  }

  .config-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  }

  .config-card {
    background: rgba(10, 20, 18, 0.6);
    border: 1px solid rgba(94, 115, 110, 0.3);
    border-radius: 0.75rem;
    padding: 1.5rem;
    transition: all 0.2s ease;
  }

  .config-card:hover {
    border-color: rgba(92, 221, 153, 0.4);
    box-shadow: 0 4px 20px rgba(92, 221, 153, 0.1);
  }

  .config-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
  }

  .config-name {
    font-size: 1.25rem;
    font-weight: 600;
    color: #bffcd8;
    margin-bottom: 0.5rem;
  }

  .config-status {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .config-status.active {
    background: rgba(34, 197, 94, 0.2);
    color: #86efac;
  }

  .config-status.disabled {
    background: rgba(94, 115, 110, 0.2);
    color: #9eb7ae;
  }

  .config-details {
    margin-bottom: 1rem;
    space-y: 0.5rem;
  }

  .config-detail {
    color: #9eb7ae;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
  }

  .config-detail strong {
    color: #bffcd8;
    font-weight: 500;
  }

  .config-detail code {
    background: rgba(94, 115, 110, 0.2);
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
  }

  .config-actions {
    padding-top: 1rem;
    border-top: 1px solid rgba(94, 115, 110, 0.2);
  }

  .delete-button {
    color: #f87171;
    background: transparent;
    border: none;
    font-weight: 500;
    cursor: pointer;
    transition: color 0.2s ease;
  }

  .delete-button:hover {
    color: #fca5a5;
  }

  /* Toggle switch */
  .toggle-switch {
    position: relative;
    width: 44px;
    height: 24px;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background: rgba(94, 115, 110, 0.4);
    transition: 0.3s;
    border-radius: 24px;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background: #e5f6ee;
    transition: 0.3s;
    border-radius: 50%;
  }

  input:checked + .toggle-slider {
    background: linear-gradient(135deg, rgba(48, 136, 95, 0.95), rgba(92, 221, 153, 0.95));
  }

  input:checked + .toggle-slider:before {
    transform: translateX(20px);
  }
</style>