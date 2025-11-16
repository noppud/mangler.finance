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

<div class="container mx-auto p-6 max-w-6xl">
  <header class="mb-8">
    <h1 class="text-3xl font-bold mb-2">MCP Configurations</h1>
    <p class="text-gray-600">
      Extend your AI assistant with Model Context Protocol servers
    </p>
  </header>

  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
      {error}
    </div>
  {/if}

  <div class="mb-6 flex justify-between items-center">
    <div class="text-sm text-gray-600">
      {configurations.length} of {maxAllowed} configurations
    </div>
    <button
      on:click={() => showAddDialog = true}
      disabled={configurations.length >= maxAllowed}
      class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
    >
      Add MCP Server
    </button>
  </div>

  {#if loading}
    <div class="flex justify-center items-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  {:else if configurations.length === 0}
    <div class="text-center py-16 bg-gray-50 rounded-lg">
      <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 mb-2">No MCP servers configured</h3>
      <p class="text-gray-600 mb-4">Add your first MCP to extend your agent's capabilities!</p>
      <button
        on:click={() => showAddDialog = true}
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        Add Your First MCP
      </button>
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {#each configurations as config}
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-semibold">{config.name}</h3>
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {config.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'} mt-1">
                {config.enabled ? 'Active' : 'Disabled'}
              </span>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.enabled}
                on:change={() => toggleMCP(config.id, config.enabled)}
                class="sr-only peer"
              />
              <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div class="space-y-2 text-sm text-gray-600">
            <div>
              <span class="font-medium">Command:</span> {config.command}
            </div>
            <div>
              <span class="font-medium">Args:</span>
              <code class="bg-gray-100 px-1 py-0.5 rounded text-xs">
                {config.args.join(' ')}
              </code>
            </div>
            {#if Object.keys(config.env || {}).length > 0}
              <div>
                <span class="font-medium">Environment:</span> {Object.keys(config.env).length} variables
              </div>
            {/if}
          </div>

          <div class="mt-4 pt-4 border-t border-gray-100">
            <button
              on:click={() => deleteMCP(config.id, config.name)}
              class="text-red-600 hover:text-red-700 text-sm font-medium"
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
  .container {
    min-height: calc(100vh - 4rem);
  }
</style>