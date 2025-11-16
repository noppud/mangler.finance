<script lang="ts">
  import { onMount } from 'svelte';
  import type { UserIdentityLink } from '$lib/types/mcp';

  let identityLink: UserIdentityLink | null = null;
  let googleEmail = '';
  let loading = true;
  let linking = false;
  let error: string | null = null;
  let success: string | null = null;

  onMount(async () => {
    await loadIdentityLink();
  });

  async function loadIdentityLink() {
    loading = true;
    error = null;

    try {
      const response = await fetch('/api/identity/current', {
        credentials: 'include'
      });

      if (response.ok) {
        identityLink = await response.json();
      } else if (response.status !== 404) {
        throw new Error('Failed to load identity link');
      }
    } catch (err) {
      console.error('Failed to load identity link:', err);
      error = 'Failed to load identity settings. Please try again.';
    } finally {
      loading = false;
    }
  }

  async function linkAccount() {
    if (!googleEmail.trim()) {
      error = 'Please enter a Google email address';
      return;
    }

    linking = true;
    error = null;
    success = null;

    try {
      const response = await fetch('/api/identity/link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ google_email: googleEmail })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to link account');
      }

      identityLink = await response.json();
      success = 'Account linked successfully! You can now use MCPs in Google Sheets.';
      googleEmail = '';
    } catch (err) {
      console.error('Failed to link account:', err);
      error = err.message || 'Failed to link account. Please try again.';
    } finally {
      linking = false;
    }
  }

  async function unlinkAccount() {
    if (!confirm('Are you sure you want to unlink your Google account? This will disable MCP access in Google Sheets.')) {
      return;
    }

    linking = true;
    error = null;
    success = null;

    try {
      const response = await fetch('/api/identity/link', {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to unlink account');
      }

      identityLink = null;
      success = 'Account unlinked successfully.';
    } catch (err) {
      console.error('Failed to unlink account:', err);
      error = 'Failed to unlink account. Please try again.';
    } finally {
      linking = false;
    }
  }
</script>

<div class="container mx-auto p-6 max-w-4xl">
  <header class="mb-8">
    <h1 class="text-3xl font-bold mb-2">Identity Linking</h1>
    <p class="text-gray-600">
      Link your Google account to use MCPs in Google Sheets
    </p>
  </header>

  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
      {error}
    </div>
  {/if}

  {#if success}
    <div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
      {success}
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center items-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  {:else}
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {#if identityLink}
        <!-- Account Linked -->
        <div class="space-y-4">
          <div class="flex items-center space-x-3">
            <svg class="w-8 h-8 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <div>
              <h3 class="text-lg font-semibold">Google Account Linked</h3>
              <p class="text-gray-600">Your MCPs are available in Google Sheets</p>
            </div>
          </div>

          <div class="bg-gray-50 rounded-lg p-4 space-y-2">
            <div>
              <span class="text-sm font-medium text-gray-700">Linked Email:</span>
              <span class="ml-2 text-sm text-gray-900">{identityLink.google_email}</span>
            </div>
            {#if identityLink.linked_at}
              <div>
                <span class="text-sm font-medium text-gray-700">Linked Since:</span>
                <span class="ml-2 text-sm text-gray-900">
                  {new Date(identityLink.linked_at).toLocaleDateString()}
                </span>
              </div>
            {/if}
          </div>

          <div class="pt-4">
            <button
              on:click={unlinkAccount}
              disabled={linking}
              class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {linking ? 'Processing...' : 'Unlink Account'}
            </button>
          </div>
        </div>
      {:else}
        <!-- Account Not Linked -->
        <div class="space-y-4">
          <div class="flex items-center space-x-3">
            <svg class="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" />
            </svg>
            <div>
              <h3 class="text-lg font-semibold">No Account Linked</h3>
              <p class="text-gray-600">Link your Google account to enable MCPs in Sheets</p>
            </div>
          </div>

          <div class="bg-blue-50 border border-blue-200 p-4 rounded-lg">
            <h4 class="font-medium text-blue-900 mb-2">Why link your account?</h4>
            <ul class="space-y-1 text-sm text-blue-800">
              <li>• Use your configured MCPs directly in Google Sheets</li>
              <li>• @mention MCPs in the chat sidebar (e.g., @gdrive)</li>
              <li>• Seamless integration between web and Sheets</li>
              <li>• Your MCPs remain private and user-scoped</li>
            </ul>
          </div>

          <form on:submit|preventDefault={linkAccount} class="space-y-4">
            <div>
              <label for="googleEmail" class="block text-sm font-medium text-gray-700 mb-1">
                Google Account Email
              </label>
              <input
                id="googleEmail"
                type="email"
                bind:value={googleEmail}
                placeholder="your-email@gmail.com"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p class="text-xs text-gray-500 mt-1">
                Enter the same email you use to access Google Sheets
              </p>
            </div>

            <button
              type="submit"
              disabled={linking}
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {linking ? 'Linking...' : 'Link Account'}
            </button>
          </form>
        </div>
      {/if}
    </div>

    <div class="mt-8 p-4 bg-gray-50 rounded-lg">
      <h3 class="font-medium text-gray-900 mb-2">How it works</h3>
      <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700">
        <li>Link your Google account email address here</li>
        <li>Configure your MCPs on the <a href="/mcp" class="text-blue-600 hover:underline">MCP page</a></li>
        <li>Open any Google Sheet with the Mangler extension</li>
        <li>Use @mentions in chat to invoke your MCPs (e.g., "@gdrive save this")</li>
      </ol>
    </div>
  </div>
{/if}
</div>