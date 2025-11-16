<script lang="ts">
	let { data } = $props();

	const errorMessage =
		data?.error === 'domain_not_allowed' ? 'Sign-in restricted by admin policy.' : null;

	const missingKindeConfig = data?.missingKindeConfig ?? false;
	const missingEnv = (data?.missingEnv as string[]) ?? [];
	const configMessage = missingKindeConfig
		? `Authentication is not configured yet. Missing env variables: ${missingEnv.join(', ')}`
		: null;

	const heroHighlights = [
		{ label: 'Active analysts', value: '300+', note: 'monitoring spreadsheets' },
		{ label: 'Sheets stabilized', value: '89%', note: 'auto-remediated' },
		{ label: 'Runbook coverage', value: '98%', note: 'critical workflows' }
	];
</script>

<svelte:head>
	<title>Sign in | Mangler</title>
</svelte:head>

<section class="dashboard">
	<div class="dashboard__grid">
		<article class="dashboard__hero">
			<div class="dashboard__eyebrow-row">
				<p class="dashboard__eyebrow">Operational console</p>
				<span class="dashboard__badge">Beta workspace</span>
			</div>
			<h1>Agents that keep your Google Sheets sharp</h1>
			<p class="dashboard__copy">
				Mangler embeds an always-on operator inside the spreadsheets your team trusts. It rewrites formulas, tags anomalies and routes escalations so humans can focus on decisions, not cells.
			</p>

			<div class="dashboard__actions">
				<a
					class={`dashboard__btn dashboard__btn--primary ${missingKindeConfig ? 'disabled' : ''}`}
					href={missingKindeConfig ? undefined : '/api/auth/login'}
					aria-disabled={missingKindeConfig}
				>
					Continue with Google
				</a>
				<a class="dashboard__btn dashboard__btn--secondary" href="/about">Learn more</a>
				<a class="dashboard__btn dashboard__btn--ghost" href="https://github.com/noppud/mangler.finance" target="_blank" rel="noopener noreferrer">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20" style="margin-right: 0.5rem;">
						<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
					</svg>
					GitHub
				</a>
			</div>

			{#if errorMessage}
				<div class="dashboard__warning dashboard__warning--error">
					{errorMessage}
				</div>
			{/if}

			{#if configMessage}
				<div class="dashboard__warning">
					<h2>Authentication not configured</h2>
					<p>{configMessage}</p>
				</div>
			{/if}

			<ul class="dashboard__highlights">
				{#each heroHighlights as item}
					<li>
						<p class="value">{item.value}</p>
						<p class="label">{item.label}</p>
						<span>{item.note}</span>
					</li>
				{/each}
			</ul>
		</article>

		<div class="dashboard__stack">
			<div class="dashboard__card dashboard__card--signin">
				<div class="dashboard__card-badge">Sheets agent access</div>
				<h3>Sign in to Mangler</h3>
				<p>Launch your workspace agent using Google Workspace.</p>
				<div class="signin-button-wrapper">
					<a
						class={`signin-button ${missingKindeConfig ? 'signin-button--disabled' : ''}`}
						href={missingKindeConfig ? undefined : '/api/auth/login'}
						aria-disabled={missingKindeConfig}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="20" height="20">
							<path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
							<path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
							<path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
							<path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
						</svg>
						Continue with Google
					</a>
				</div>
				<p class="signin-note">Only operators provisioned for Sheet-mangler can access this stack.</p>
			</div>

			<div class="dashboard__card dashboard__card--features">
				<h3>Key capabilities</h3>
				<ul>
					<li>
						<strong>Formula validation</strong>
						<span>Detect and fix errors automatically</span>
					</li>
					<li>
						<strong>Data integrity</strong>
						<span>Cross-reference checking enabled</span>
					</li>
					<li>
						<strong>Privacy scanning</strong>
						<span>PII detection and alerts</span>
					</li>
				</ul>
			</div>
		</div>
	</div>

	<div class="dashboard__lower-grid">
		<article class="dashboard__card dashboard__card--actions">
			<h3>Quick start</h3>
			<p class="muted">Get started with Mangler in minutes.</p>
			<ul>
				<li>Run clean-up passes across finance and ops sheets without opening them.</li>
				<li>Auto-comment and notify stakeholders when assumptions drift.</li>
				<li>Compose multi-step workflows across Sheets, Gmail and Drive.</li>
			</ul>
		</article>

		<article class="dashboard__card dashboard__card--powered">
			<div class="dashboard__card-header">
				<h3>AI-powered analysis</h3>
				<span class="pill">Advanced</span>
			</div>
			<p>
				Advanced spreadsheet analysis powered by AI to detect issues, suggest fixes, and maintain data integrity across your organization.
			</p>
			<ul>
				<li>Automatic formula validation and error detection.</li>
				<li>Real-time data consistency checks across sheets.</li>
				<li>One-click fixes for common spreadsheet issues.</li>
				<li>Streaming chat interface for instant assistance.</li>
			</ul>
		</article>
	</div>
</section>

<style>
	.dashboard {
		display: flex;
		flex-direction: column;
		gap: 2rem;
		min-height: calc(100vh - 4rem);
		padding: 0;
	}

	.dashboard__grid {
		display: grid;
		grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
		gap: 1.75rem;
	}

	.dashboard__hero {
		padding: clamp(2rem, 4vw, 3.5rem);
		border-radius: 2rem;
		background: radial-gradient(circle at top right, rgba(53, 255, 184, 0.18), transparent 55%),
			linear-gradient(135deg, rgba(6, 16, 12, 0.95), rgba(16, 39, 31, 0.9));
		border: 1px solid rgba(85, 193, 151, 0.35);
		box-shadow: 0 45px 80px rgba(3, 10, 8, 0.65);
	}

	.dashboard__eyebrow-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.dashboard__eyebrow {
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.35em;
		color: rgba(183, 246, 218, 0.6);
		margin: 0;
	}

	.dashboard__badge {
		padding: 0.25rem 0.75rem;
		border-radius: 999px;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.2em;
		background: rgba(60, 236, 163, 0.15);
		border: 1px solid rgba(60, 236, 163, 0.5);
		color: #c9ffe7;
	}

	h1 {
		font-size: clamp(2.4rem, 4vw, 3.6rem);
		margin: 0 0 1rem;
		color: #f6fff9;
		letter-spacing: -0.04em;
	}

	.dashboard__copy {
		color: rgba(221, 248, 237, 0.85);
		margin-bottom: 1.75rem;
		line-height: 1.7;
		max-width: 48ch;
	}

	.dashboard__actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
	}

	.dashboard__btn {
		border-radius: 999px;
		padding: 0.85rem 1.4rem;
		border: 1px solid transparent;
		font-weight: 600;
		cursor: pointer;
		text-decoration: none;
		text-align: center;
		transition: transform 150ms ease, box-shadow 150ms ease, border-color 0.2s ease;
		display: inline-flex;
		align-items: center;
	}

	.dashboard__btn--primary {
		background: linear-gradient(135deg, #2de28c, #69fabc);
		color: #02150d;
		box-shadow: 0 20px 30px rgba(47, 226, 140, 0.3);
	}

	.dashboard__btn--primary.disabled {
		background: rgba(47, 226, 140, 0.2);
		color: rgba(2, 21, 13, 0.5);
		cursor: not-allowed;
		box-shadow: none;
	}

	.dashboard__btn--secondary {
		background: rgba(47, 226, 140, 0.12);
		color: #c2ffe7;
		border-color: rgba(47, 226, 140, 0.4);
	}

	.dashboard__btn--ghost {
		background: rgba(5, 12, 10, 0.55);
		color: #d2fbe9;
		border-color: rgba(91, 147, 129, 0.5);
	}

	.dashboard__btn:hover:not(.disabled) {
		transform: translateY(-1px);
	}

	.dashboard__highlights {
		margin: 2rem 0 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 1rem;
	}

	.dashboard__highlights li {
		padding: 1rem;
		border-radius: 1.25rem;
		background: rgba(4, 12, 10, 0.6);
		border: 1px solid rgba(81, 122, 112, 0.4);
	}

	.dashboard__highlights .value {
		margin: 0;
		font-size: clamp(1.5rem, 3vw, 2.4rem);
		font-weight: 600;
		color: #f5fff9;
	}

	.dashboard__highlights .label {
		margin: 0.25rem 0 0.15rem;
		text-transform: uppercase;
		letter-spacing: 0.2em;
		font-size: 0.75rem;
		color: rgba(162, 196, 186, 0.8);
	}

	.dashboard__highlights span {
		font-size: 0.85rem;
		color: rgba(198, 225, 215, 0.65);
	}

	.dashboard__stack {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.dashboard__card {
		padding: 1.75rem;
		border-radius: 1.5rem;
		background: rgba(4, 9, 8, 0.75);
		border: 1px solid rgba(82, 136, 117, 0.4);
		box-shadow: 0 25px 50px rgba(2, 5, 4, 0.65);
	}

	.dashboard__card--signin {
		background: radial-gradient(circle at top, rgba(60, 236, 163, 0.1), transparent 60%),
			rgba(4, 9, 8, 0.85);
	}

	.dashboard__card-badge {
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

	.dashboard__card h3 {
		margin: 0 0 0.75rem;
		font-size: 1.3rem;
	}

	.dashboard__card p {
		margin: 0 0 1.25rem;
		color: rgba(211, 240, 230, 0.8);
		line-height: 1.6;
	}

	.dashboard__card--features ul {
		list-style: none;
		padding: 0;
		margin: 1.25rem 0 0;
		display: grid;
		gap: 0.75rem;
	}

	.dashboard__card--features li {
		display: flex;
		justify-content: space-between;
		font-size: 0.9rem;
		color: #c5e6d8;
	}

	.signin-button-wrapper {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 1rem;
	}

	.signin-button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		min-width: 240px;
		padding: 0.9rem 1.2rem;
		border-radius: 0.75rem;
		text-decoration: none;
		font-weight: 600;
		color: #03150d;
		background: linear-gradient(120deg, #2ba36a, #3fd08b, #84f4bf);
		box-shadow: 0 15px 35px rgba(63, 208, 139, 0.35);
		transition: transform 150ms ease, box-shadow 150ms ease;
	}

	.signin-button:hover {
		transform: translateY(-2px);
		box-shadow: 0 22px 45px rgba(132, 244, 191, 0.35);
	}

	.signin-button--disabled,
	.signin-button--disabled:hover {
		background: rgba(62, 179, 122, 0.25);
		color: rgba(12, 39, 27, 0.7);
		box-shadow: none;
		cursor: not-allowed;
		transform: none;
	}

	.signin-note {
		margin: 0;
		font-size: 0.85rem;
		color: rgba(188, 235, 212, 0.75);
		text-align: center;
	}

	.dashboard__lower-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 1.5rem;
	}

	.dashboard__card--actions ul,
	.dashboard__card--powered ul {
		margin: 1rem 0 0;
		padding-left: 1.1rem;
		color: rgba(202, 229, 217, 0.85);
		line-height: 1.8;
	}

	.dashboard__card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.pill {
		padding: 0.25rem 0.9rem;
		border-radius: 999px;
		border: 1px solid rgba(255, 255, 255, 0.2);
		font-size: 0.8rem;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: rgba(236, 255, 248, 0.85);
	}

	.muted {
		color: rgba(202, 229, 217, 0.7);
		margin: 0.25rem 0 0;
	}

	.dashboard__warning {
		padding: 1.5rem;
		border-radius: 1.25rem;
		background: rgba(255, 171, 102, 0.12);
		border: 1px solid rgba(255, 171, 102, 0.4);
		color: #ffe4c7;
	}

	.dashboard__warning--error {
		background: rgba(239, 68, 68, 0.12);
		border: 1px solid rgba(239, 68, 68, 0.4);
		color: #fecaca;
	}

	.dashboard__warning h2 {
		margin: 0 0 0.5rem;
		font-size: 1.2rem;
	}

	.dashboard__warning p {
		margin: 0;
	}

	@media (max-width: 900px) {
		.dashboard__grid {
			grid-template-columns: 1fr;
		}

		.dashboard__actions {
			flex-direction: column;
		}
	}
</style>