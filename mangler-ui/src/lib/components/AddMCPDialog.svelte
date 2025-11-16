<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { MCP_PRESETS } from '$lib/types/mcp';

  const dispatch = createEventDispatcher();

  let name = '';
  let command = 'npx';
  let args = '';
  let envVars: { key: string; value: string }[] = [];
  let submitting = false;
  let error: string | null = null;

  function applyPreset(preset: typeof MCP_PRESETS[0]) {
    name = preset.name;
    command = preset.command;
    args = preset.args.join(' ');
    // Clear env vars when applying preset
    envVars = [];
  }

  function addEnvVar() {
    envVars = [...envVars, { key: '', value: '' }];
  }

  function removeEnvVar(index: number) {
    envVars = envVars.filter((_, i) => i !== index);
  }

  async function handleSubmit() {
    error = null;
    submitting = true;

    try {
      const argsArray = args.split(' ').filter(a => a.trim());
      const env = Object.fromEntries(
        envVars
          .filter(v => v.key.trim())
          .map(v => [v.key, v.value])
      );

      const response = await fetch('/api/mcp/configurations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name,
          command,
          args: argsArray,
          env,
          mcp_type: 'stdio'
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create MCP configuration');
      }

      dispatch('added');
      dispatch('close');
    } catch (err) {
      console.error('Failed to create MCP:', err);
      error = err.message || 'Failed to create MCP configuration. Please try again.';
    } finally {
      submitting = false;
    }
  }

  function handleOverlayClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      dispatch('close');
    }
  }
</script>

<div
  class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
  on:click={handleOverlayClick}
>
  <div class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold">Add MCP Server</h2>
      <button
        on:click={() => dispatch('close')}
        class="text-gray-400 hover:text-gray-600"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Presets -->
    <div class="mb-6">
      <p class="text-sm font-medium text-gray-700 mb-3">Quick presets:</p>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
        {#each MCP_PRESETS as preset}
          <button
            type="button"
            on:click={() => applyPreset(preset)}
            class="p-3 text-left border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-center space-x-2">
              <span class="text-2xl">{preset.icon}</span>
              <span class="text-sm font-medium">{preset.name}</span>
            </div>
          </button>
        {/each}
      </div>
    </div>

    {#if error}
      <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
        {error}
      </div>
    {/if}

    <form on:submit|preventDefault={handleSubmit}>
      <div class="space-y-4">
        <!-- Name -->
        <div>
          <label for="name" class="block text-sm font-medium text-gray-700 mb-1">
            Name
          </label>
          <input
            id="name"
            type="text"
            bind:value={name}
            placeholder="My MCP Server"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <!-- Command -->
        <div>
          <label for="command" class="block text-sm font-medium text-gray-700 mb-1">
            Command
          </label>
          <select
            id="command"
            bind:value={command}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="npx">npx</option>
            <option value="node">node</option>
            <option value="python">python</option>
            <option value="python3">python3</option>
            <option value="uvx">uvx</option>
          </select>
        </div>

        <!-- Arguments -->
        <div>
          <label for="args" class="block text-sm font-medium text-gray-700 mb-1">
            Arguments
          </label>
          <input
            id="args"
            type="text"
            bind:value={args}
            placeholder="@modelcontextprotocol/server-name"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p class="text-xs text-gray-500 mt-1">
            Space-separated arguments for the command
          </p>
        </div>

        <!-- Environment Variables -->
        <div>
          <div class="flex justify-between items-center mb-2">
            <label class="block text-sm font-medium text-gray-700">
              Environment Variables (Optional)
            </label>
            <button
              type="button"
              on:click={addEnvVar}
              class="text-sm text-blue-600 hover:text-blue-700"
            >
              + Add Variable
            </button>
          </div>

          {#each envVars as envVar, i}
            <div class="flex space-x-2 mb-2">
              <input
                type="text"
                bind:value={envVar.key}
                placeholder="KEY"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                bind:value={envVar.value}
                placeholder="value"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                on:click={() => removeEnvVar(i)}
                class="px-3 py-2 text-red-600 hover:text-red-700"
              >
                ×
              </button>
            </div>
          {/each}
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-end space-x-3 mt-6">
        <button
          type="button"
          on:click={() => dispatch('close')}
          class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? 'Creating...' : 'Create'}
        </button>
      </div>
    </form>
  </div>
</div>