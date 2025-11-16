<script lang="ts">
	import favicon from '$lib/assets/logo-mark-dark.svg';

	let { children, data } = $props();

	const missingKindeConfig = data?.missingKindeConfig;
	const missingEnv = data?.missingEnv ?? [];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<header class="app-header">
	<div class="app-header__inner">
		<div class="app-header__brand">
			<a href="/">Mangler</a>
		</div>

		{#if data?.isAuthenticated}
			<div class="app-header__user">
				<span class="app-header__email">{data.user?.email}</span>
				<a class="app-header__link" href="/api/auth/logout" data-sveltekit-reload>Logout</a>
			</div>
		{:else}
			<a class="app-header__link" href="/login">Login</a>
		{/if}
	</div>

	{#if missingKindeConfig}
		<div class="app-banner">
			<span>Authentication not configured.</span>
			<span class="app-banner__vars">Missing: {missingEnv.join(', ')}</span>
		</div>
	{/if}
</header>

<main class="app-main">
	{@render children()}
</main>

<style>
	:global(body) {
		margin: 0;
		background-color: #050b09;
		color: #e5f6ee;
		font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
		min-height: 100vh;
	}

	a {
		color: inherit;
	}

	.app-header {
		padding: 1rem 1.5rem 0.5rem;
		background: rgba(4, 11, 10, 0.95);
		position: sticky;
		top: 0;
		z-index: 10;
		border-bottom: 1px solid rgba(94, 115, 110, 0.2);
	}

	.app-header__inner {
		max-width: 1100px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.app-header__brand a {
		font-weight: 800;
		text-decoration: none;
		color: #bffcd8;
		font-size: clamp(1.2rem, 2vw, 1.75rem);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.app-header__user {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		font-size: 0.95rem;
		color: #9eb7ae;
	}

	.app-header__email {
		color: #d2fff0;
	}

	.app-header__link {
		text-decoration: none;
		font-weight: 700;
		padding: 0.5rem 1.2rem;
		border-radius: 999px;
		border: 1px solid rgba(84, 187, 130, 0.75);
		color: #03140d;
		background: linear-gradient(135deg, rgba(48, 136, 95, 0.95), rgba(92, 221, 153, 0.95));
		box-shadow: 0 10px 20px rgba(58, 201, 136, 0.25);
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}

	.app-header__link:hover {
		transform: translateY(-1px);
		box-shadow: 0 14px 30px rgba(92, 221, 153, 0.35);
	}

	.app-banner {
		margin: 0.75rem auto 0;
		max-width: 1100px;
		padding: 0.65rem 0.9rem;
		border-radius: 0.75rem;
		background-color: rgba(113, 213, 179, 0.12);
		border: 1px solid rgba(113, 213, 179, 0.4);
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.85rem;
		color: #b7f5da;
		gap: 0.5rem;
	}

	.app-banner__vars {
		color: rgba(254, 243, 199, 0.8);
		font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
		font-size: 0.8rem;
	}

	.app-main {
		padding: 3rem 1.5rem 4rem;
		min-height: calc(100vh - 4rem);
	}

	.app-main :global(section) {
		color: #f8fafc;
	}
</style>
