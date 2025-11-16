<script lang="ts">
	import { browser } from '$app/environment';
	import { env as publicEnv } from '$env/dynamic/public';

	let { data } = $props();

	const BACKEND_URL = 'https://fintech-hackathon-production.up.railway.app';
	const SERVICE_ACCOUNT_EMAIL =
		'googlesheetworker@fintech-hackathon-478313.iam.gserviceaccount.com';
	const GOOGLE_CLIENT_ID = publicEnv.PUBLIC_GOOGLE_CLIENT_ID || '';
	const GOOGLE_OAUTH_SCOPE = [
		'https://www.googleapis.com/auth/script.projects',
		'https://www.googleapis.com/auth/drive',
		'https://www.googleapis.com/auth/spreadsheets'
	].join(' ');

	type GoogleTokenResponse = { access_token?: string; expires_in?: number };
	type GoogleTokenError = { error?: string; error_description?: string };

	type AccessInfo = {
		hasAccess: boolean;
		name?: string;
		spreadsheetId?: string;
		serviceAccountEmail?: string;
		owners?: { emailAddress?: string; displayName?: string }[];
	};

	let step = $state<'input' | 'check-access' | 'installing' | 'success' | 'error'>('input');
	let spreadsheetUrl = $state('');
	let spreadsheetId = $state('');
	let serviceAccountEmail = $state(SERVICE_ACCOUNT_EMAIL);
	let errorMessage = $state('');
	let successMessage = $state('');
	let spreadsheetName = $state('');
	let scriptId = $state('');
	let lastAccessResult = $state<AccessInfo | null>(null);
	let installFailed = $state(false);
	let googleAccessToken = $state('');
	let googleTokenExpiry = $state(0);
	let googleAuthError = $state('');
	let googleScriptPromise: Promise<void> | null = null;

	function resetGoogleToken() {
		googleAccessToken = '';
		googleTokenExpiry = 0;
	}

	function extractSpreadsheetId(url: string): string | null {
		// Extract ID from URL like: https://docs.google.com/spreadsheets/d/1abc.../edit
		const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
		return match ? match[1] : null;
	}

	async function ensureGoogleIdentityLoaded() {
		if (!browser) {
			throw new Error('Google authorization is only available in the browser.');
		}

		if (window.google?.accounts?.oauth2) {
			return;
		}

		if (!googleScriptPromise) {
			googleScriptPromise = new Promise((resolve, reject) => {
				const script = document.createElement('script');
				script.src = 'https://accounts.google.com/gsi/client';
				script.async = true;
				script.defer = true;
				script.onload = () => resolve();
				script.onerror = () => reject(new Error('Failed to load Google authentication library'));
				document.head.appendChild(script);
			});
		}

		await googleScriptPromise;

		if (!window.google?.accounts?.oauth2) {
			throw new Error('Google authentication library is unavailable.');
		}
	}

	async function requestGoogleAccessToken(forcePrompt = false): Promise<string> {
		if (!GOOGLE_CLIENT_ID) {
			throw new Error('Google OAuth client ID is not configured.');
		}

		const bufferMs = 60_000; // refresh token if expiring in < 60s
		if (googleAccessToken && googleTokenExpiry - bufferMs > Date.now()) {
			return googleAccessToken;
		}

		await ensureGoogleIdentityLoaded();

		return await new Promise((resolve, reject) => {
			if (!window.google?.accounts?.oauth2) {
				reject(new Error('Google authentication library is unavailable.'));
				return;
			}

			try {
				const client = window.google.accounts.oauth2.initTokenClient({
					client_id: GOOGLE_CLIENT_ID,
					scope: GOOGLE_OAUTH_SCOPE,
					callback: (response: GoogleTokenResponse) => {
						if (response && response.access_token) {
							googleAccessToken = response.access_token;
							const expiresIn = Number(response.expires_in || 3600);
							googleTokenExpiry = Date.now() + expiresIn * 1000;
							resolve(response.access_token);
						} else {
							reject(new Error('No access token returned from Google.'));
						}
					},
					error_callback: (error: GoogleTokenError) => {
						const message = error?.error_description || error?.error || 'Authorization failed.';
						reject(new Error(message));
					}
				});

				if (!client) {
					reject(new Error('Unable to initialize Google OAuth client.'));
					return;
				}

				const requestConfig: { prompt?: string; scope: string } = {
					scope: GOOGLE_OAUTH_SCOPE
				};

				if (forcePrompt || !googleAccessToken) {
					requestConfig.prompt = 'consent';
				}

				client.requestAccessToken(requestConfig);
			} catch (err: any) {
				reject(err);
			}
		});
	}

	async function handleNext() {
		errorMessage = '';
		googleAuthError = '';
		lastAccessResult = null;
		installFailed = false;

		// Extract spreadsheet ID from URL
		const id = extractSpreadsheetId(spreadsheetUrl);
		if (!id) {
			errorMessage = 'Invalid Google Sheets URL. Please paste the full URL from your browser.';
			return;
		}

		spreadsheetId = id;
		step = 'check-access';

		// Check if service account has access
		try {
			const response = await fetch(`${BACKEND_URL}/extension/check-access`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ spreadsheet_id: spreadsheetId })
			});

			const result = await response.json();

			if (result.hasAccess) {
				lastAccessResult = result;
				spreadsheetName = result.name || 'Unknown Spreadsheet';
				// Auto-proceed to installation
				await installExtension();
			} else {
				lastAccessResult = result;
				errorMessage = `Service account doesn't have access yet. Please share the sheet with: ${serviceAccountEmail}`;
				step = 'error';
			}
		} catch (err: any) {
			errorMessage = `Failed to check access: ${err.message || err}`;
			step = 'error';
		}
	}

	async function installExtension() {
		step = 'installing';
		errorMessage = '';
		installFailed = false;
		googleAuthError = '';

		let accessToken: string;

		try {
			accessToken = await requestGoogleAccessToken();
		} catch (authError: any) {
			googleAuthError = authError?.message || 'Google authorization failed.';
			errorMessage = googleAuthError;
			step = 'error';
			return;
		}

		try {
			const response = await fetch(`${BACKEND_URL}/extension/install`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					spreadsheet_id: spreadsheetId,
					user_email: data?.user?.email,
					google_access_token: accessToken
				})
			});

			const result = await response.json();

			if (result.success) {
				scriptId = result.scriptId || '';
				successMessage = result.message || 'Extension installed successfully!';
				step = 'success';
			} else {
				const scopeError =
					/ACCESS_TOKEN_SCOPE_INSUFFICIENT|insufficient authentication scopes/i.test(
						result.message || result.error || ''
					);

				if (scopeError) {
					resetGoogleToken();
					googleAuthError =
						'Google authorization is missing the required Apps Script permissions. Please accept the Google prompt again when you retry.';
				}

				installFailed = true;
				errorMessage = result.message || result.error || 'Installation failed';
				step = 'error';
			}
		} catch (err: any) {
			resetGoogleToken();
			errorMessage = `Installation failed: ${err.message || err}`;
			step = 'error';
		}
	}

	function reset() {
		step = 'input';
		spreadsheetUrl = '';
		spreadsheetId = '';
		errorMessage = '';
		successMessage = '';
		spreadsheetName = '';
		scriptId = '';
		lastAccessResult = null;
		installFailed = false;
	}

	function copyEmail() {
		if (serviceAccountEmail) {
			navigator.clipboard.writeText(serviceAccountEmail);
		}
	}
</script>

<svelte:head>
	<title>Install Extension | Mangler</title>
</svelte:head>

<section class="extension-page">
	<div class="header">
		<a href="/" class="back-link">← Back to Dashboard</a>
		<h1>Install <span>Mangler</span> Extension</h1>
		<p class="subtitle">Bring the Mangler Sheets agent into your doc in two quick steps.</p>
	</div>

	<div class="content-wrapper">
		<!-- Step 1: Share Sheet -->
		{#if step === 'input'}
			<div class="card install-card">
				<h2>Step 1: Share Your Google Sheet</h2>
				<p class="instruction">
					First, share your Google Sheet with our service account so we can install the extension.
				</p>

				<div class="service-account-box">
					<label for="email">Service Account Email:</label>
					<div class="email-display">
						<input
							type="text"
							id="email"
							value={serviceAccountEmail}
							readonly
							class="email-input"
						/>
						<button type="button" onclick={copyEmail} class="copy-btn" title="Copy email">
							📋
						</button>
					</div>
					<p class="hint">Copy this email and share your sheet with Editor permissions</p>
				</div>

					<h2>Step 2: Enter Your Sheet URL</h2>
				<p class="instruction">
					After sharing, paste the full URL of your Google Sheet below:
				</p>

				<form
					onsubmit={(e) => {
						e.preventDefault();
						handleNext();
					}}
				>
					<input
						type="url"
						bind:value={spreadsheetUrl}
						placeholder="https://docs.google.com/spreadsheets/d/..."
						class="url-input"
						required
					/>

					<button type="submit" class="install-btn">Install Extension</button>
				</form>
			</div>
		{/if}

		<!-- Checking Access -->
		{#if step === 'check-access'}
			<div class="card status-card">
				<div class="spinner"></div>
				<h2>Checking Access...</h2>
				<p>Verifying that the service account can access your spreadsheet</p>
			</div>
		{/if}

		<!-- Installing -->
		{#if step === 'installing'}
			<div class="card status-card">
				<div class="spinner"></div>
				<h2>Installing Extension...</h2>
				<p>Adding Mangler Extension to "{spreadsheetName}"</p>
			</div>
		{/if}

		<!-- Success -->
		{#if step === 'success'}
			<div class="card success-card">
				<div class="success-icon">✅</div>
				<h2>Extension Installed Successfully!</h2>
				<p class="success-message">{successMessage}</p>

				<div class="success-details">
					<p><strong>Spreadsheet:</strong> {spreadsheetName}</p>
					<p><strong>Script ID:</strong> {scriptId}</p>
				</div>

				<div class="next-steps">
					<h3>Next Steps:</h3>
					<ol>
						<li>Open your Google Sheet</li>
						<li>
							Refresh the page (you may need to wait a few seconds for the menu to appear)
						</li>
						<li>
							Click <strong>Mangler → Open Mangler</strong> from the menu
						</li>
						<li>Start chatting with your spreadsheet!</li>
					</ol>
				</div>

				<div class="button-group">
					<a href={`https://docs.google.com/spreadsheets/d/${spreadsheetId}/edit`} target="_blank" class="open-sheet-btn">
						Open Spreadsheet
					</a>
					<button type="button" onclick={reset} class="reset-btn">Install to Another Sheet</button>
				</div>
			</div>
		{/if}

		<!-- Error -->
		{#if step === 'error'}
			<div class="card error-card">
				<div class="error-icon" aria-hidden="true">
					<span class="error-cross"></span>
				</div>
				<h2>Installation Failed</h2>
				<p class="error-message">{errorMessage}</p>

				{#if lastAccessResult?.hasAccess}
					<div class="status-stack">
						<div class="status-row status-pass">
							<span>Access Check</span>
							<span>Passed</span>
						</div>
						{#if installFailed}
							<div class="status-row status-fail">
								<span>Script Installation</span>
								<span>Failed</span>
							</div>
						{/if}
					</div>
				{/if}

				<div class="error-help">
					<h3>Troubleshooting:</h3>
					<ul>
						<li>Make sure you've shared the sheet with the service account email</li>
						<li>Ensure the service account has <strong>Editor</strong> permissions</li>
						<li>Wait a few seconds after sharing before trying again</li>
						<li>Check that the spreadsheet URL is correct</li>
					</ul>
				</div>

				<button type="button" onclick={reset} class="retry-btn">Try Again</button>
			</div>
		{/if}

	</div>
</section>

<style>
	:global(body) {
		background-color: #020617;
		color: #f8fafc;
	}

	.extension-page {
		max-width: 800px;
		margin: 0 auto;
		padding: 2rem;
	}

	.header {
		margin-bottom: 3rem;
		text-align: center;
	}

	.back-link {
		display: inline-flex;
		align-items: center;
		color: #93c5fd;
		text-decoration: none;
		font-size: 0.9rem;
		margin-bottom: 1rem;
		transition: color 0.2s ease;
	}

	.back-link:hover {
		color: #60a5fa;
	}

	h1 {
		font-size: 2.25rem;
		margin: 0.5rem 0 1rem;
		color: #94a3b8;
		font-weight: 600;
	}

	h1 span {
		display: block;
		font-size: clamp(2.8rem, 5vw, 3.5rem);
		color: #f8fafc;
		letter-spacing: -0.02em;
	}

	.subtitle {
		color: #94a3b8;
		font-size: 1.1rem;
		margin: 0;
	}

	.content-wrapper {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.card {
		background: rgba(15, 23, 42, 0.6);
		border: 1px solid rgba(148, 163, 184, 0.2);
		border-radius: 1rem;
		padding: 2rem;
	}

	.card h2 {
		font-size: 1.5rem;
		margin: 0 0 1rem;
		color: #f8fafc;
	}

	.card h3 {
		font-size: 1.1rem;
		margin: 1.5rem 0 0.75rem;
		color: #e2e8f0;
	}

	.instruction {
		color: #94a3b8;
		margin-bottom: 1.5rem;
		line-height: 1.6;
	}

	.service-account-box {
		background: rgba(41, 227, 255, 0.08);
		border: 1px solid rgba(41, 227, 255, 0.25);
		border-radius: 0.75rem;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.service-account-box label {
		display: block;
		font-size: 0.9rem;
		color: #93c5fd;
		margin-bottom: 0.5rem;
		font-weight: 500;
	}

	.email-display {
		display: flex;
		gap: 0.5rem;
	}

	.email-input {
		flex: 1;
		padding: 0.75rem;
		background: rgba(15, 23, 42, 0.8);
		border: 1px solid rgba(148, 163, 184, 0.3);
		border-radius: 0.5rem;
		color: #f8fafc;
		font-family: monospace;
		font-size: 0.9rem;
	}

	.copy-btn {
		padding: 0.75rem 1rem;
		background: #29e3ff;
		border: none;
		border-radius: 0.5rem;
		cursor: pointer;
		font-size: 1.2rem;
		transition: all 0.2s ease;
	}

	.copy-btn:hover {
		background: #15a8c3;
		transform: translateY(-1px);
	}

	.hint {
		margin: 0.75rem 0 0;
		font-size: 0.85rem;
		color: #7dd3fc;
	}

	.url-input {
		width: 100%;
		padding: 1rem;
		background: rgba(15, 23, 42, 0.8);
		border: 2px solid rgba(148, 163, 184, 0.3);
		border-radius: 0.75rem;
		color: #f8fafc;
		font-size: 1rem;
		margin-bottom: 1rem;
		transition: border-color 0.2s ease;
	}

	.url-input:focus {
		outline: none;
		border-color: #3b82f6;
	}

	.install-btn {
		width: 100%;
		padding: 1rem 1.5rem;
		background: linear-gradient(135deg, #3b82f6, #8b5cf6);
		color: #fff;
		border: none;
		border-radius: 0.75rem;
		font-size: 1.1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.install-btn:hover {
		transform: translateY(-2px);
		box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
	}

	.status-card {
		text-align: center;
		padding: 3rem 2rem;
	}

	.spinner {
		width: 50px;
		height: 50px;
		border: 4px solid rgba(59, 130, 246, 0.2);
		border-top-color: #3b82f6;
		border-radius: 50%;
		margin: 0 auto 1.5rem;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.success-card,
	.error-card {
		text-align: center;
	}

	.success-icon {
		font-size: 4rem;
		margin-bottom: 1rem;
	}

	.error-icon {
		width: 96px;
		height: 96px;
		border-radius: 50%;
		background: rgba(148, 163, 184, 0.15);
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0 auto 1rem;
	}

	.error-cross {
		position: relative;
		display: block;
		width: 44px;
		height: 44px;
	}

	.error-cross::before,
	.error-cross::after {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		width: 44px;
		height: 4px;
		background: #cbd5f5;
		border-radius: 999px;
		transform-origin: center;
	}

	.error-cross::before {
		transform: translate(-50%, -50%) rotate(45deg);
	}

	.error-cross::after {
		transform: translate(-50%, -50%) rotate(-45deg);
	}

	.success-message,
	.error-message {
		color: #94a3b8;
		font-size: 1.1rem;
		margin-bottom: 2rem;
	}

	.status-stack {
		margin-bottom: 2rem;
		text-align: left;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.status-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-radius: 0.75rem;
		padding: 0.75rem 1rem;
		font-weight: 500;
		border: 1px solid rgba(148, 163, 184, 0.2);
	}

	.status-pass {
		background: rgba(34, 197, 94, 0.08);
		color: #4ade80;
	}

	.status-fail {
		background: rgba(248, 113, 113, 0.08);
		color: #fca5a5;
	}

	.success-details {
		background: rgba(34, 197, 94, 0.1);
		border: 1px solid rgba(34, 197, 94, 0.3);
		border-radius: 0.75rem;
		padding: 1.5rem;
		margin-bottom: 2rem;
		text-align: left;
	}

	.success-details p {
		margin: 0.5rem 0;
		color: #94a3b8;
	}

	.next-steps {
		text-align: left;
		margin-bottom: 2rem;
	}

	.next-steps ol {
		color: #94a3b8;
		line-height: 1.8;
	}

	.button-group {
		display: flex;
		gap: 1rem;
		justify-content: center;
	}

	.open-sheet-btn,
	.reset-btn,
	.retry-btn {
		padding: 0.9rem 1.5rem;
		border-radius: 0.75rem;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
		border: none;
		text-decoration: none;
		display: inline-block;
	}

	.open-sheet-btn {
		background: #22c55e;
		color: #fff;
	}

	.open-sheet-btn:hover {
		background: #16a34a;
		transform: translateY(-1px);
	}

	.reset-btn,
	.retry-btn {
		background: rgba(148, 163, 184, 0.2);
		color: #e2e8f0;
		border: 1px solid rgba(148, 163, 184, 0.3);
	}

	.reset-btn:hover,
	.retry-btn:hover {
		background: rgba(148, 163, 184, 0.3);
	}

	.error-help {
		text-align: left;
		margin-bottom: 2rem;
	}

	.error-help ul {
		color: #94a3b8;
		line-height: 1.8;
	}

</style>
