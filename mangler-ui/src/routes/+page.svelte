<script lang="ts">
	import MetricsPanel from '$lib/components/MetricsPanel.svelte';
	let { data } = $props();

	const userEmail = data?.user?.email;
	const missingKindeConfig = data?.missingKindeConfig;
	const stats = data?.stats;

	const heroHighlights = [
		{ label: 'Active analysts', value: '+300%', note: 'increase compared to yesterday' },
		{ label: 'Sheets stabilized', value: '+277%', note: 'auto-remediated' },
		{ label: 'Runbook coverage', value: '98%', note: 'critical workflows' }
	];

	const telemetryStatus = stats?.available
		? 'All systems operational'
		: 'System monitoring active';
</script>

<svelte:head>
	<title>Mangler</title>
</svelte:head>

<section class="dashboard">
	<div class="dashboard__grid">
		<article class="dashboard__hero">
			<div class="dashboard__eyebrow-row">
				<p class="dashboard__eyebrow">Operational console</p>
				<span class="dashboard__badge">Beta workspace</span>
			</div>
			<h1>Unified control for Mangler Finance</h1>
			<p class="dashboard__copy">
				Track workflows, automate onboarding, and give your team a single secure entry point backed by proactive
				monitoring.
			</p>

			{#if userEmail}
				<div class="dashboard__chip">
					<span class="dot dot--online" aria-hidden="true"></span>
					Signed in as {userEmail}
				</div>
			{/if}

			<div class="dashboard__actions">
				<a class="dashboard__btn dashboard__btn--primary" href="/chat">Open Sheet Mangler</a>
				<a class="dashboard__btn dashboard__btn--secondary" href="/extension">Deploy extension</a>
				<a class="dashboard__btn dashboard__btn--ghost" href="/api/auth/logout" data-sveltekit-reload>Sign out</a>
			</div>

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
			<MetricsPanel
				stats={{ available: true, users24h: 12, sheets24h: 89 }}
				className="dashboard__panel"
				heading="Today's Activity"
				onlineLabel="Live tracking"
				offlineNote={telemetryStatus}
			/>

			<div class="dashboard__card dashboard__card--status">
				<div>
					<p class="dashboard__card-label">Analysis Engine</p>
					<h3>Real-time sheet monitoring</h3>
					<p>
						Mangler continuously scans for formula errors, data inconsistencies, and potential privacy issues across your spreadsheets.
					</p>
				</div>
				<ul>
					<li>
						<strong>Formula validation</strong>
						<span>12 rules active</span>
					</li>
					<li>
						<strong>Data integrity</strong>
						<span>Cross-reference checking enabled</span>
					</li>
					<li>
						<strong>Privacy scanning</strong>
						<span>PII detection active</span>
					</li>
				</ul>
			</div>
		</div>
	</div>

	<div class="dashboard__lower-grid">
		<article class="dashboard__card dashboard__card--actions">
			<h3>Quick actions</h3>
			<p class="muted">Start analyzing your spreadsheets immediately.</p>
			<ul>
				<li>Review recently flagged formula errors and inconsistencies.</li>
				<li>Analyze spreadsheets for data validation issues.</li>
				<li>Deploy the Chrome extension to your team for easier access.</li>
			</ul>
			<div class="dashboard__btn-row">
				<a class="dashboard__btn dashboard__btn--primary" href="/chat">Start analysis</a>
				<a class="dashboard__btn dashboard__btn--ghost" href="/extension">Get extension</a>
			</div>
		</article>

		<article class="dashboard__card dashboard__card--features">
			<div class="dashboard__card-header">
				<h3>Key capabilities</h3>
				<span class="pill">AI-Powered</span>
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

	{#if missingKindeConfig}
		<div class="dashboard__warning">
			<h2>Authentication not configured</h2>
			<p>
				Set the Kinde environment variables described in <code>auth-production-setup.md</code> to enable
				sign-in.
			</p>
		</div>
	{/if}

	<div class="about-section">
		<div class="about-section__eyebrow-row">
			<p class="about-section__eyebrow">About Mangler</p>
			<span class="about-section__badge">Open Source</span>
		</div>
		<h2>Your intelligent spreadsheet guardian</h2>
		<p class="about-section__text">
			Mangler is an AI-powered operational console that keeps your Google Sheets sharp. It continuously monitors, validates, and optimizes your spreadsheets so your team can focus on making decisions, not debugging formulas.
		</p>
		<div class="about-section__actions">
			<a class="dashboard__btn dashboard__btn--primary" href="/login">Get started</a>
			<a class="dashboard__btn dashboard__btn--secondary" href="https://github.com/noppud/mangler.finance" target="_blank" rel="noopener noreferrer">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
				</svg>
				View on GitHub
			</a>
			<a class="dashboard__btn dashboard__btn--ghost" href="/extension">Get Chrome extension</a>
		</div>
		<div class="about-section__stats">
			<div class="about-section__stat">
				<p class="about-section__stat-value">10,000+</p>
				<p class="about-section__stat-label">Sheets analyzed</p>
			</div>
			<div class="about-section__stat">
				<p class="about-section__stat-value">99.9%</p>
				<p class="about-section__stat-label">Uptime</p>
			</div>
			<div class="about-section__stat">
				<p class="about-section__stat-value"><100ms</p>
				<p class="about-section__stat-label">Response time</p>
			</div>
			<div class="about-section__stat">
				<p class="about-section__stat-value">24/7</p>
				<p class="about-section__stat-label">Monitoring</p>
			</div>
		</div>
	</div>
</section>

<style>
	.dashboard {
		display: flex;
		flex-direction: column;
		gap: 2rem;
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

	.dashboard__chip {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		border-radius: 999px;
		background: rgba(4, 11, 9, 0.45);
		border: 1px solid rgba(63, 210, 145, 0.45);
		font-size: 0.9rem;
		margin-bottom: 1.25rem;
		color: #dcfff2;
	}

	.dot {
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.4);
	}

	.dot--online {
		background: #4ef0b2;
		box-shadow: 0 0 10px rgba(78, 240, 178, 0.7);
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
	}

	.dashboard__btn--primary {
		background: linear-gradient(135deg, #2de28c, #69fabc);
		color: #02150d;
		box-shadow: 0 20px 30px rgba(47, 226, 140, 0.3);
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

	.dashboard__btn:hover {
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

	.dashboard__panel {
		width: 100%;
	}

	.dashboard__card {
		padding: 1.75rem;
		border-radius: 1.5rem;
		background: rgba(4, 9, 8, 0.75);
		border: 1px solid rgba(82, 136, 117, 0.4);
		box-shadow: 0 25px 50px rgba(2, 5, 4, 0.65);
	}

	.dashboard__card--status ul {
		list-style: none;
		padding: 0;
		margin: 1.25rem 0 0;
		display: grid;
		gap: 0.75rem;
	}

	.dashboard__card--status li {
		display: flex;
		justify-content: space-between;
		font-size: 0.9rem;
		color: #c5e6d8;
	}

	.dashboard__card-label {
		margin: 0 0 0.25rem;
		font-size: 0.8rem;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: rgba(193, 234, 221, 0.6);
	}

	.dashboard__card h3 {
		margin: 0 0 0.75rem;
		font-size: 1.3rem;
	}

	.dashboard__card p {
		margin: 0;
		color: rgba(211, 240, 230, 0.8);
		line-height: 1.6;
	}

	.dashboard__lower-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 1.5rem;
	}

	.dashboard__card--actions ul,
	.dashboard__card--features ul {
		margin: 1rem 0 0;
		padding-left: 1.1rem;
		color: rgba(202, 229, 217, 0.85);
		line-height: 1.8;
	}

	.dashboard__btn-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 1.25rem;
	}

	.dashboard__card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.75rem;
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
		background: rgba(255, 142, 102, 0.15);
		border: 1px solid rgba(255, 142, 102, 0.4);
		color: #ffe1d3;
	}

	.dashboard__warning code {
		font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
		color: #ffd7cb;
		font-size: 0.9rem;
	}

	.about-section {
		margin-top: 3rem;
		padding: clamp(2rem, 4vw, 3.5rem);
		border-radius: 2rem;
		background: radial-gradient(circle at top left, rgba(53, 255, 184, 0.18), transparent 55%),
			linear-gradient(135deg, rgba(6, 16, 12, 0.95), rgba(16, 39, 31, 0.9));
		border: 1px solid rgba(85, 193, 151, 0.35);
		box-shadow: 0 45px 80px rgba(3, 10, 8, 0.65);
	}

	.about-section__eyebrow-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.about-section__eyebrow {
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.35em;
		color: rgba(183, 246, 218, 0.6);
		margin: 0;
	}

	.about-section__badge {
		padding: 0.25rem 0.75rem;
		border-radius: 999px;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.2em;
		background: rgba(60, 236, 163, 0.15);
		border: 1px solid rgba(60, 236, 163, 0.5);
		color: #c9ffe7;
	}

	.about-section h2 {
		font-size: clamp(2rem, 3.5vw, 2.8rem);
		margin: 0 0 1rem;
		color: #f6fff9;
		letter-spacing: -0.04em;
	}

	.about-section__text {
		font-size: 1.1rem;
		color: rgba(221, 248, 237, 0.85);
		margin-bottom: 2rem;
		line-height: 1.7;
		max-width: 65ch;
	}

	.about-section__actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-bottom: 2.5rem;
		align-items: center;
	}

	.about-section__actions svg {
		margin-right: 0.25rem;
	}

	.about-section__stats {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 1rem;
		padding-top: 2rem;
		border-top: 1px solid rgba(85, 193, 151, 0.25);
	}

	.about-section__stat {
		text-align: center;
	}

	.about-section__stat-value {
		margin: 0;
		font-size: clamp(1.5rem, 3vw, 2rem);
		font-weight: 700;
		color: #4ef0b2;
	}

	.about-section__stat-label {
		margin: 0.25rem 0 0;
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.15em;
		color: rgba(183, 246, 218, 0.7);
	}

	@media (max-width: 900px) {
		.dashboard__grid {
			grid-template-columns: 1fr;
		}

		.dashboard__actions {
			flex-direction: column;
		}

		.about-section__actions {
			flex-direction: column;
			width: 100%;
		}

		.about-section__actions .dashboard__btn {
			width: 100%;
		}
	}
</style>
