<script lang="ts">
	import { page } from '$app/stores';

	let { children, data } = $props();

	const missingKindeConfig = data?.missingKindeConfig;
	const missingEnv = data?.missingEnv ?? [];

	const navLinks = [
		{ href: '/', label: 'Overview' },
		{ href: '/pricing', label: 'Pricing' },
		{ href: '/chat', label: 'Sheet Mangler' },
		{ href: '/extension', label: 'Extension' }
	];
</script>

<svelte:head>
	<link rel="icon" href="/mangler.svg" sizes="any" type="image/svg+xml" />
	<link rel="icon" href="/mangler.png" sizes="32x32" type="image/png" />
</svelte:head>

<div class="app-container">
	<header class="app-header">
		<div class="app-header__inner">
			<div class="app-header__brand">
				<a href="/">Mangler</a>
				<p class="app-header__tagline">Operational console</p>
			</div>

			<nav class="app-header__nav" aria-label="Primary">
				{#each navLinks as link}
					{#if data?.isAuthenticated || link.href === '/' || link.href === '/pricing'}
						<a
							href={link.href}
							class={`app-header__nav-link ${$page.url.pathname === link.href ? 'is-active' : ''}`.trim()}
							aria-current={$page.url.pathname === link.href ? 'page' : undefined}
						>
							{link.label}
						</a>
					{:else}
						<span
							class="app-header__nav-link app-header__nav-link--disabled"
							title="Please login to access this feature"
						>
							{link.label}
						</span>
					{/if}
				{/each}
			</nav>

			<div class="app-header__actions">
				{#if data?.isAuthenticated}
					<div class="app-header__user">
						<span class="app-header__email">{data.user?.email}</span>
						<a class="app-header__link" href="/api/auth/logout" data-sveltekit-reload>
							Logout
						</a>
					</div>
				{:else}
					<a class="app-header__link" href="/login">
						Login
					</a>
				{/if}
			</div>
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

	<footer class="app-footer">
		<div class="app-footer__content">
			<div class="app-footer__info">
				<p class="app-footer__copyright">© 2024 Mangler Finance</p>
				<p class="app-footer__tagline">Intelligent spreadsheet guardian</p>
			</div>
			<div class="app-footer__links">
				<a
					href="https://github.com/noppud/mangler.finance"
					target="_blank"
					rel="noopener noreferrer"
					class="app-footer__github"
					aria-label="View on GitHub"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
						<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
					</svg>
					<span>View on GitHub</span>
				</a>
			</div>
		</div>
	</footer>
</div>

<style>
	:global(*, *::before, *::after) {
		box-sizing: border-box;
	}

	:global(:root) {
		color-scheme: dark;
	}

	:global(body) {
		margin: 0;
		min-height: 100vh;
		font-family: 'Space Grotesk', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
		background: radial-gradient(circle at top, rgba(64, 217, 133, 0.08), transparent 45%),
			rgb(2, 6, 5);
		color: #effff8;
		line-height: 1.6;
		display: flex;
		flex-direction: column;
	}

	:global(#app) {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	:global(body)::before {
		content: '';
		position: fixed;
		top: -10%;
		left: 50%;
		width: 60vw;
		height: 60vw;
		background: radial-gradient(circle, rgba(80, 245, 171, 0.15), transparent 60%);
		transform: translateX(-50%);
		z-index: -1;
		filter: blur(20px);
	}

	a {
		color: inherit;
	}

	.app-container {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	.app-header {
		padding: 1rem 1.5rem 0.5rem;
		background: rgba(4, 9, 8, 0.85);
		backdrop-filter: blur(18px);
		position: sticky;
		top: 0;
		z-index: 10;
		border-bottom: 1px solid rgba(132, 241, 188, 0.08);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
		flex-shrink: 0;
	}

	.app-header__inner {
		max-width: 1200px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 1rem;
	}

	.app-header__brand a {
		font-weight: 800;
		text-decoration: none;
		color: #d6ffe9;
		font-size: clamp(1.25rem, 2.5vw, 1.85rem);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.app-header__tagline {
		margin: 0.1rem 0 0;
		font-size: 0.8rem;
		letter-spacing: 0.28em;
		text-transform: uppercase;
		color: rgba(214, 255, 233, 0.6);
	}

	.app-header__nav {
		display: flex;
		justify-content: center;
		gap: 0.35rem;
		padding: 0.35rem;
		border-radius: 999px;
		border: 1px solid rgba(94, 194, 151, 0.25);
		background: rgba(6, 13, 11, 0.7);
	}

	.app-header__nav-link {
		text-decoration: none;
		font-size: 0.9rem;
		padding: 0.45rem 0.9rem;
		border-radius: 999px;
		color: rgba(219, 255, 239, 0.7);
		transition: color 0.2s ease, background 0.2s ease;
	}

	.app-header__nav-link:hover:not(.app-header__nav-link--disabled),
	.app-header__nav-link.is-active {
		color: #04120b;
		background: linear-gradient(135deg, rgba(28, 209, 128, 0.95), rgba(64, 232, 173, 0.9));
	}

	.app-header__nav-link--disabled {
		opacity: 0.4;
		cursor: not-allowed;
		color: rgba(219, 255, 239, 0.4);
	}

	.app-header__actions {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.app-header__user {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		font-size: 0.95rem;
		color: #a1cbc1;
	}

	.app-header__email {
		color: #f3fff9;
		font-weight: 600;
	}

	.app-header__link {
		text-decoration: none;
		font-weight: 700;
		padding: 0.5rem 1.2rem;
		border-radius: 999px;
		border: 1px solid rgba(64, 232, 173, 0.4);
		color: #052016;
		background: linear-gradient(135deg, #4ef0b2, #7afcc7);
		box-shadow: 0 12px 35px rgba(44, 214, 144, 0.25);
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}

	.app-header__link:hover {
		transform: translateY(-1px);
		box-shadow: 0 18px 35px rgba(64, 232, 173, 0.35);
	}

	.app-banner {
		margin: 0.75rem auto 0;
		max-width: 1200px;
		padding: 0.8rem 1rem;
		border-radius: 1rem;
		background: rgba(255, 171, 102, 0.12);
		border: 1px solid rgba(255, 171, 102, 0.4);
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.9rem;
		color: #ffe4c7;
		gap: 0.5rem;
	}

	.app-banner__vars {
		color: rgba(255, 244, 223, 0.9);
		font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
		font-size: 0.8rem;
	}

	.app-main {
		flex: 1;
		padding: 3.5rem 1.5rem 2rem;
		display: flex;
		flex-direction: column;
	}

	.app-main > :global(*) {
		max-width: 1200px;
		margin: 0 auto;
		width: 100%;
	}

	.app-main :global(section) {
		color: #f8fafc;
	}

	.app-footer {
		background: rgba(4, 9, 8, 0.85);
		backdrop-filter: blur(18px);
		border-top: 1px solid rgba(132, 241, 188, 0.08);
		padding: 2rem 1.5rem;
		margin-top: auto;
		flex-shrink: 0;
	}

	.app-footer__content {
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 2rem;
	}

	.app-footer__info p {
		margin: 0.25rem 0;
	}

	.app-footer__copyright {
		color: #f6fff9;
		font-weight: 600;
		font-size: 0.95rem;
	}

	.app-footer__tagline {
		color: rgba(214, 255, 233, 0.6);
		font-size: 0.85rem;
		letter-spacing: 0.15em;
		text-transform: uppercase;
	}

	.app-footer__github {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.25rem;
		border-radius: 999px;
		background: rgba(6, 13, 11, 0.7);
		border: 1px solid rgba(94, 194, 151, 0.25);
		color: rgba(219, 255, 239, 0.8);
		text-decoration: none;
		transition: background 0.2s ease, transform 0.2s ease;
		font-size: 0.9rem;
	}

	.app-footer__github:hover {
		background: rgba(94, 194, 151, 0.15);
		color: #4ef0b2;
		transform: translateY(-2px);
	}

	@media (max-width: 900px) {
		.app-header__inner {
			grid-template-columns: 1fr;
			text-align: center;
		}

		.app-header__nav {
			justify-content: center;
		}

		.app-header__actions {
			justify-content: center;
		}

		.app-header__user {
			justify-content: center;
		}

		.app-footer__content {
			flex-direction: column;
			text-align: center;
		}

		.app-footer__info {
			order: 2;
		}

		.app-footer__links {
			order: 1;
		}
	}
</style>
