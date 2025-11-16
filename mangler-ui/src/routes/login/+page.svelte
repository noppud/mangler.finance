<script lang="ts">
	import MetricsPanel from '$lib/components/MetricsPanel.svelte';
	let { data } = $props();

	const errorMessage =
		data?.error === 'domain_not_allowed' ? 'Sign-in restricted by admin policy.' : null;

	const missingKindeConfig = data?.missingKindeConfig ?? false;
	const missingEnv = (data?.missingEnv as string[]) ?? [];
	const stats = data?.stats;
	const configMessage = missingKindeConfig
		? `Authentication is not configured yet. Missing env variables: ${missingEnv.join(', ')}`
		: null;
</script>

<svelte:head>
	<title>Sign in | Mangler</title>
</svelte:head>

<section class="login">
	<div class="login__shell">
		<div class="login__headline">
			<p class="eyebrow">Sheet-mangler / control plane</p>
			<h1>Agents that keep your Google Sheets honest.</h1>
			<p class="hero__copy">
				Mangler embeds an always-on operator inside the spreadsheets your team trusts. It rewrites
				formulas, tags anomalies and routes escalations so humans can focus on decisions, not cells.
			</p>
			<ul class="hero__list">
				<li>Run clean-up passes across finance and ops sheets without opening them.</li>
				<li>Auto-comment and notify stakeholders when assumptions drift.</li>
				<li>Compose multi-step workflows across Sheets, Gmail and Drive.</li>
			</ul>

			<div class="login__metrics">
				<MetricsPanel
					stats={stats}
					heading="Last 24 hours"
					offlineNote="Connect Supabase env vars to surface live usage metrics."
				/>
			</div>
		</div>

		<div class="login__card">
			<div class="login__badge">Sheets agent access</div>
			<h2>Sign in to Mangler</h2>
			<p class="login__subtitle">Launch your workspace agent using Google Workspace.</p>

			{#if errorMessage}
				<p class="login__error">{errorMessage}</p>
			{/if}

			{#if configMessage}
				<p class="login__warning">{configMessage}</p>
			{/if}

			<div class="login__button-wrapper">
				<a
					class={`login__button ${missingKindeConfig ? 'login__button--disabled' : ''}`}
					href={missingKindeConfig ? undefined : '/api/auth/login'}
					aria-disabled={missingKindeConfig}
				>
					Continue with Google
				</a>
			</div>
			<p class="login__footnote">Only operators provisioned for Sheet-mangler can access this stack.</p>
		</div>
	</div>
</section>

<style>
	:global(body) {
		background-color: #050b09;
		color: #e5f6ee;
		font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
	}

	.login {
		min-height: calc(100vh - 4rem);
		padding: clamp(2.5rem, 5vw, 5rem) clamp(1.5rem, 4vw, 6rem);
		background: radial-gradient(circle at top, rgba(67, 187, 131, 0.18), transparent 55%),
			rgba(5, 11, 9, 0.95);
	}

	.login__shell {
		position: relative;
		z-index: 1;
		max-width: 1080px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
		gap: clamp(2rem, 4vw, 4rem);
		align-items: center;
	}

	.login__headline {
		padding-right: clamp(0, 5vw, 4rem);
	}

	.eyebrow {
		text-transform: uppercase;
		letter-spacing: 0.35em;
		font-size: 0.75rem;
		color: rgba(144, 244, 184, 0.85);
		margin-bottom: 1rem;
	}

	h1 {
		font-size: clamp(2.75rem, 5vw, 4rem);
		margin: 0 0 1rem;
		line-height: 1.15;
	}

	.hero__copy {
		color: rgba(210, 244, 227, 0.9);
		font-size: 1.05rem;
		line-height: 1.9;
		margin-bottom: 1.5rem;
		max-width: 46ch;
	}

	.hero__list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}

	.hero__list li {
		display: flex;
		gap: 0.6rem;
		align-items: flex-start;
		color: rgba(210, 244, 227, 0.9);
	}

	.hero__list li::before {
		content: '';
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: #40ff9f;
		margin-top: 0.5rem;
		box-shadow: 0 0 16px rgba(64, 255, 159, 0.45);
	}

	.login__metrics {
		margin-top: 2rem;
		max-width: 420px;
	}

	.login__card {
		width: min(420px, 100%);
		padding: clamp(2rem, 4vw, 2.75rem);
		background: rgba(9, 21, 17, 0.92);
		border: 1px solid rgba(79, 180, 133, 0.4);
		border-radius: 1.1rem;
		box-shadow: 0 25px 75px rgba(3, 10, 8, 0.85);
	}

	.login__badge {
		display: inline-flex;
		padding: 0.35rem 0.75rem;
		border-radius: 999px;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		background-color: rgba(76, 214, 147, 0.15);
		color: #a4f9cd;
		margin-bottom: 1rem;
	}

	.login__subtitle {
		margin: 0.75rem 0 1.5rem;
		color: rgba(188, 235, 212, 0.85);
	}

	.login__error,
	.login__warning {
		margin: 0 0 1rem;
		padding: 0.8rem 1rem;
		border-radius: 0.75rem;
		font-size: 0.9rem;
		line-height: 1.4;
	}

	.login__error {
		background-color: rgba(239, 68, 68, 0.12);
		border: 1px solid rgba(239, 68, 68, 0.4);
		color: #fecaca;
	}

	.login__warning {
		background-color: rgba(251, 191, 36, 0.12);
		border: 1px solid rgba(251, 191, 36, 0.4);
		color: #fde68a;
	}

	.login__button-wrapper {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.login__button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 280px;
		padding: 0.9rem 1rem;
		border-radius: 0.75rem;
		text-decoration: none;
		font-weight: 600;
		color: #03150d;
		background: linear-gradient(120deg, #2ba36a, #3fd08b, #84f4bf);
		box-shadow: 0 15px 35px rgba(63, 208, 139, 0.35);
		transition: transform 150ms ease, box-shadow 150ms ease;
	}

	.login__button:hover {
		transform: translateY(-2px);
		box-shadow: 0 22px 45px rgba(132, 244, 191, 0.35);
	}

	.login__button--disabled,
	.login__button--disabled:hover {
		background: rgba(62, 179, 122, 0.25);
		color: rgba(12, 39, 27, 0.7);
		box-shadow: none;
		cursor: not-allowed;
		transform: none;
	}

	.login__footnote {
		margin-top: 1rem;
		font-size: 0.85rem;
		color: rgba(188, 235, 212, 0.75);
	}

	@media (max-width: 640px) {
		.login__card {
			padding: 2rem;
		}
	}
</style>
