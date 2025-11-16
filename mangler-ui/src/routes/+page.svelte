<script lang="ts">
	import MetricsPanel from '$lib/components/MetricsPanel.svelte';
	let { data } = $props();

	const userEmail = data?.user?.email;
	const missingKindeConfig = data?.missingKindeConfig;
	const stats = data?.stats;
</script>

<svelte:head>
	<title>Mangler</title>
</svelte:head>

<section class="dashboard">
	<div class="dashboard__hero">
		<p class="dashboard__eyebrow">Operational Console</p>
		<h1>Unified control for Mangler Finance</h1>
		<p class="dashboard__copy">
			Track workflows, automate onboarding and give your team a single secure entry point.
		</p>

		{#if userEmail}
			<div class="dashboard__chip">Signed in as {userEmail}</div>
		{/if}

		<div class="dashboard__actions">
			<a class="dashboard__btn dashboard__btn--primary" href="/chat">Open Chat</a>
			<a class="dashboard__btn dashboard__btn--secondary" href="/extension">Get Extension</a>
			<a class="dashboard__btn dashboard__btn--ghost" href="/api/auth/logout" data-sveltekit-reload>Sign out</a>
		</div>
	</div>

	<MetricsPanel
		stats={stats}
		className="dashboard__panel"
		offlineNote="Connect Supabase env vars to surface live usage metrics."
	/>

	{#if missingKindeConfig}
		<div class="dashboard__warning">
			<h2>Authentication not configured</h2>
			<p>
				Set the Kinde environment variables described in <code>auth-production-setup.md</code> to enable
				sign-in.
			</p>
		</div>
	{/if}
</section>

<style>
	.dashboard {
		max-width: 1100px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
		gap: 2rem;
	}

	.dashboard__hero {
		padding: 2.5rem;
		border-radius: 1.5rem;
		background: linear-gradient(135deg, rgba(15, 32, 28, 0.95), rgba(28, 50, 44, 0.85));
		box-shadow: 0 35px 60px rgba(5, 9, 8, 0.55);
		border: 1px solid rgba(82, 110, 100, 0.6);
	}

	.dashboard__eyebrow {
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.2em;
		color: rgba(181, 214, 201, 0.85);
		margin-bottom: 0.75rem;
	}

	h1 {
		font-size: clamp(2rem, 4vw, 3rem);
		margin: 0 0 1rem;
		color: #f3fff9;
	}

	.dashboard__copy {
		color: rgba(212, 238, 227, 0.85);
		margin-bottom: 1.5rem;
		line-height: 1.7;
	}

	.dashboard__chip {
		display: inline-flex;
		padding: 0.5rem 0.85rem;
		border-radius: 999px;
		background: rgba(5, 12, 10, 0.5);
		border: 1px solid rgba(101, 136, 123, 0.5);
		font-size: 0.9rem;
		margin-bottom: 1.2rem;
		color: #d2fff0;
	}

	.dashboard__actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}

	.dashboard__btn {
		border-radius: 0.9rem;
		padding: 0.85rem 1.2rem;
		border: none;
		font-weight: 600;
		cursor: pointer;
		text-decoration: none;
		text-align: center;
		transition: transform 150ms ease, box-shadow 150ms ease;
	}

	.dashboard__btn--primary {
		background: linear-gradient(135deg, #2ba36a, #3fd08b);
		color: #04130d;
		box-shadow: 0 15px 30px rgba(63, 208, 139, 0.35);
	}

	.dashboard__btn--ghost {
		background: rgba(5, 12, 10, 0.6);
		color: #cdeee0;
		border: 1px solid rgba(95, 130, 118, 0.6);
	}

	.dashboard__btn:hover {
		transform: translateY(-1px);
	}

	.dashboard__warning {
		grid-column: 1 / -1;
		padding: 1.5rem;
		border-radius: 1rem;
		background: rgba(191, 97, 71, 0.12);
		border: 1px solid rgba(191, 97, 71, 0.3);
		color: #f9c5b5;
	}

	.dashboard__warning code {
		font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
		color: #ffd7cb;
		font-size: 0.9rem;
	}
</style>
