<script lang="ts">
	import { browser } from '$app/environment';
	import { env as publicEnv } from '$env/dynamic/public';
	import { onMount } from 'svelte';

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
	let testerStatus = $state<'idle' | 'pending' | 'success' | 'error'>('idle');
	let testerError = $state('');
	let testerPromise: Promise<boolean> | null = null;
	let fileCopyState = $state<Record<string, 'idle' | 'copied' | 'error'>>({});

	const MANUAL_FILES = [
		{
			name: 'Code.gs',
			url: '/extension/Code.gs',
			description: 'Main script logic. Create/replace Code.gs in Apps Script.'
		},
		{
			name: 'Sidebar.html',
			url: '/extension/Sidebar.html',
			description: 'Sidebar UI. Create an HTML file named Sidebar and paste this content.'
		},
		{
			name: 'appsscript.json',
			url: '/extension/appsscript.json',
			description: 'Manifest file. Replace the default project manifest with this JSON.'
		}
	] as const;

	function resetGoogleToken() {
		googleAccessToken = '';
		googleTokenExpiry = 0;
	}

	onMount(() => {
		ensureTesterRegistered().catch(() => {
			// errors handled via testerStatus/testerError state
		});
	});

	async function ensureTesterRegistered(force = false): Promise<boolean> {
		const userEmail = data?.user?.email;

		if (!browser || !userEmail) {
			return true;
		}

		if (testerStatus === 'success' && !force) {
			return true;
		}

		if (testerPromise && !force) {
			return testerPromise;
		}

		testerPromise = (async () => {
			try {
				testerStatus = 'pending';
				testerError = '';

				const response = await fetch(`${BACKEND_URL}/extension/register-tester`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ user_email: userEmail })
				});

				if (response.status === 404) {
					// Backend hasn't been deployed with tester support yet. Treat as success.
					testerStatus = 'success';
					return true;
				}

				const result = await response.json();

				if (!response.ok) {
					// OAuth consent screen not configured - this is OK, installation can still proceed
					// User will need to manually add themselves as a tester in GCP Console
					const errorMsg = result?.detail || 'Unable to register as OAuth tester.';

					// Check if it's the OAuth consent screen error
					if (errorMsg.includes('OAuth consent screen not configured')) {
						testerStatus = 'error';
						testerError = errorMsg;
						// Return true anyway - installation can proceed without this
						console.warn('OAuth tester registration failed (consent screen not configured), but installation can continue:', errorMsg);
						return true;
					}

					throw new Error(errorMsg);
				}

				testerStatus = 'success';
				return true;
			} catch (err: any) {
				testerStatus = 'error';
				testerError = err?.message || 'Failed to register as OAuth tester.';
				// Allow installation to proceed even if tester registration fails
				console.warn('OAuth tester registration failed, but installation can continue:', err);
				return true;
			} finally {
				testerPromise = null;
			}
		})();

		return testerPromise;
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

		const testerReady = await ensureTesterRegistered();
		if (!testerReady) {
			errorMessage = testerError || 'Unable to authorize your Google account. Please try again.';
			step = 'error';
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

	async function copyFile(fileName: string, url: string) {
		try {
			const response = await fetch(url);
			if (!response.ok) throw new Error('Unable to load file contents');
			const text = await response.text();
			await navigator.clipboard.writeText(text);
			fileCopyState = { ...fileCopyState, [fileName]: 'copied' };
			setTimeout(() => {
				fileCopyState = { ...fileCopyState, [fileName]: 'idle' };
			}, 2000);
		} catch (err) {
			console.error('Failed to copy file', err);
			fileCopyState = { ...fileCopyState, [fileName]: 'error' };
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

				{#if testerStatus === 'pending'}
					<div class="tester-notice tester-notice--pending">
						Adding your Google account to the OAuth tester list…
					</div>
				{:else if testerStatus === 'success'}
					<div class="tester-notice tester-notice--success">
						You're authorized to approve the Mangler extension install.
					</div>
				{:else if testerStatus === 'error'}
					<div class="tester-notice tester-notice--warning">
						<strong>⚠️ OAuth Tester Registration Skipped</strong>
						<p style="margin-top: 0.5rem; font-size: 0.9em;">
							We couldn't automatically add you to the OAuth tester list. You can still install the extension,
							but you'll need to manually add your email ({data?.user?.email}) as a test user in the
							<a
								href="https://console.cloud.google.com/apis/credentials/consent?project=fintech-hackathon-478313"
								target="_blank"
								rel="noopener noreferrer"
								style="color: #4ADE80; text-decoration: underline;"
							>
								Google Cloud Console
							</a>
							after installation.
						</p>
						<details style="margin-top: 0.5rem; font-size: 0.85em; opacity: 0.8;">
							<summary style="cursor: pointer;">Technical details</summary>
							<p style="margin-top: 0.25rem;">{testerError}</p>
						</details>
					</div>
				{/if}

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

				<div class="manual-fallback">
					<h3>Manual Installation Fallback</h3>
					<p>
						If the automated install fails, you can add the script manually:
					</p>
					<ol>
						<li>Open your sheet → Extensions → Apps Script</li>
						<li>Replace the files below with our versions</li>
						<li>Refresh the sheet and open the Mangler menu</li>
					</ol>
					<div class="manual-files">
						{#each MANUAL_FILES as file}
							<div class="manual-file-card">
								<div>
									<div class="manual-file-name">{file.name}</div>
									<p>{file.description}</p>
								</div>
								<div class="manual-file-actions">
									<a href={file.url} download={file.name}>Download</a>
									<button type="button" onclick={() => copyFile(file.name, file.url)}>
										{#if fileCopyState[file.name] === 'copied'}
											Copied!
										{:else if fileCopyState[file.name] === 'error'}
											Retry Copy
										{:else}
											Copy
										{/if}
									</button>
								</div>
							</div>
						{/each}
					</div>
				</div>

				<button type="button" onclick={reset} class="retry-btn">Try Again</button>
			</div>
		{/if}

	</div>
</section>

<style>
	:global(body) {
		background-color: #050b09;
		color: #e5f6ee;
	}

	.extension-page {
		max-width: 800px;
		margin: 0 auto;
		padding: clamp(2rem, 4vw, 3rem);
	}

	.header {
		margin-bottom: 3rem;
		text-align: center;
	}

	.back-link {
		display: inline-flex;
		align-items: center;
		color: #8df9c1;
		text-decoration: none;
		font-size: 0.9rem;
		margin-bottom: 1rem;
		transition: color 0.2s ease;
	}

	.back-link:hover {
		color: #b0ffd7;
	}

	h1 {
		font-size: 2.25rem;
		margin: 0.5rem 0 1rem;
		color: rgba(166, 221, 197, 0.85);
		font-weight: 600;
	}

	h1 span {
		display: block;
		font-size: clamp(2.8rem, 5vw, 3.5rem);
		color: #f4fff9;
		letter-spacing: -0.02em;
	}

	.subtitle {
		color: rgba(188, 235, 212, 0.8);
		font-size: 1.1rem;
		margin: 0;
	}

	.content-wrapper {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.card {
		background: rgba(10, 19, 16, 0.85);
		border: 1px solid rgba(77, 133, 112, 0.4);
		border-radius: 1rem;
		padding: 2rem;
		box-shadow: 0 30px 45px rgba(3, 8, 6, 0.7);
	}

	.card h2 {
		font-size: 1.5rem;
		margin: 0 0 1rem;
		color: #e9fff4;
	}

	.card h3 {
		font-size: 1.1rem;
		margin: 1.5rem 0 0.75rem;
		color: #c9f1dd;
	}

	.instruction {
		color: rgba(189, 231, 212, 0.85);
		margin-bottom: 1.5rem;
		line-height: 1.6;
	}

	.service-account-box {
		background: rgba(63, 208, 139, 0.12);
		border: 1px solid rgba(63, 208, 139, 0.35);
		border-radius: 0.75rem;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.service-account-box label {
		display: block;
		font-size: 0.9rem;
		color: #9cfacc;
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
		background: rgba(4, 12, 10, 0.9);
		border: 1px solid rgba(108, 163, 140, 0.5);
		border-radius: 0.5rem;
		color: #d9ffef;
		font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
		font-size: 0.9rem;
	}

	.copy-btn {
		padding: 0.75rem 1rem;
		background: linear-gradient(140deg, #2ba36a, #3fd08b);
		border: none;
		border-radius: 0.5rem;
		cursor: pointer;
		font-size: 1.2rem;
		color: #03150d;
		transition: all 0.2s ease;
	}

	.copy-btn:hover {
		background: linear-gradient(140deg, #3fd08b, #84f4bf);
		transform: translateY(-1px);
	}

	.hint {
		margin: 0.75rem 0 0;
		font-size: 0.85rem;
		color: #acf7d3;
	}

	.tester-notice {
		margin: 0 0 1.5rem;
		padding: 0.85rem 1rem;
		border-radius: 0.75rem;
		font-size: 0.95rem;
	}

	.tester-notice--pending {
		background: rgba(28, 112, 83, 0.35);
		border: 1px solid rgba(71, 171, 131, 0.65);
		color: #c5ffe8;
	}

	.tester-notice--success {
		background: rgba(36, 167, 107, 0.25);
		border: 1px solid rgba(76, 214, 147, 0.6);
		color: #aefcd5;
	}

	.tester-notice--error {
		background: rgba(248, 113, 113, 0.12);
		border: 1px solid rgba(248, 113, 113, 0.35);
		color: #fecaca;
	}

	.tester-notice--warning {
		background: rgba(251, 191, 36, 0.12);
		border: 1px solid rgba(251, 191, 36, 0.4);
		color: #fde68a;
	}

	.tester-notice--warning a {
		color: #4ADE80;
		text-decoration: underline;
	}

	.tester-notice--warning a:hover {
		color: #86EFAC;
	}

	.url-input {
		width: 100%;
		padding: 1rem;
		background: rgba(4, 12, 10, 0.9);
		border: 2px solid rgba(108, 163, 140, 0.45);
		border-radius: 0.75rem;
		color: #e9fff4;
		font-size: 1rem;
		margin-bottom: 1rem;
		transition: border-color 0.2s ease, box-shadow 0.2s ease;
	}

	.url-input:focus {
		outline: none;
		border-color: #3fd08b;
		box-shadow: 0 0 0 3px rgba(63, 208, 139, 0.2);
	}

	.install-btn {
		width: 100%;
		padding: 1rem 1.5rem;
		background: linear-gradient(135deg, #2ba36a, #3fd08b, #84f4bf);
		color: #03160d;
		border: none;
		border-radius: 0.75rem;
		font-size: 1.1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
		box-shadow: 0 18px 40px rgba(63, 208, 139, 0.35);
	}

	.install-btn:hover {
		transform: translateY(-2px);
		box-shadow: 0 24px 50px rgba(132, 244, 191, 0.4);
	}

	.status-card {
		text-align: center;
		padding: 3rem 2rem;
	}

	.spinner {
		width: 50px;
		height: 50px;
		border: 4px solid rgba(63, 208, 139, 0.2);
		border-top-color: #3fd08b;
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
		color: rgba(190, 230, 212, 0.85);
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
		border: 1px solid rgba(103, 169, 144, 0.35);
	}

	.status-pass {
		background: rgba(63, 208, 139, 0.15);
		color: #78f6b9;
	}

	.status-fail {
		background: rgba(248, 113, 113, 0.08);
		color: #fca5a5;
	}

	.success-details {
		background: rgba(20, 46, 36, 0.9);
		border: 1px solid rgba(82, 149, 122, 0.45);
		border-radius: 0.75rem;
		padding: 1.5rem;
		margin-bottom: 2rem;
		text-align: left;
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
	}

	.success-details p {
		margin: 0.5rem 0;
		color: rgba(190, 231, 214, 0.85);
	}

	.next-steps {
		text-align: left;
		margin-bottom: 2rem;
	}

	.next-steps ol {
		color: rgba(190, 231, 214, 0.85);
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
		background: linear-gradient(135deg, #2ba36a, #3fd08b);
		color: #04160e;
		box-shadow: 0 12px 25px rgba(63, 208, 139, 0.3);
	}

	.open-sheet-btn:hover {
		background: linear-gradient(135deg, #3fd08b, #84f4bf);
		transform: translateY(-1px);
	}

	.reset-btn,
	.retry-btn {
		background: rgba(7, 16, 13, 0.7);
		color: #c7eddc;
		border: 1px solid rgba(103, 169, 144, 0.5);
	}

	.reset-btn:hover,
	.retry-btn:hover {
		background: rgba(11, 25, 20, 0.85);
	}

	.error-help {
		text-align: left;
		margin-bottom: 2rem;
	}

	.error-help ul {
		color: rgba(190, 231, 214, 0.85);
		line-height: 1.8;
	}

	.manual-fallback {
		text-align: left;
		margin-top: 2rem;
		padding-top: 1.5rem;
		border-top: 1px solid rgba(148, 163, 184, 0.25);
	}

	.manual-fallback ol {
		margin: 0 0 1rem;
		padding-left: 1.25rem;
		color: rgba(190, 231, 214, 0.85);
	}

	.manual-files {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.manual-file-card {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		padding: 1rem;
		border-radius: 0.75rem;
		background: rgba(8, 18, 15, 0.9);
		border: 1px solid rgba(92, 149, 122, 0.35);
	}

	.manual-file-name {
		font-weight: 600;
	}

	.manual-file-actions {
		display: flex;
		gap: 0.75rem;
		align-items: center;
	}

	.manual-file-actions a {
		color: #8df9c1;
		text-decoration: none;
		font-size: 0.9rem;
	}

	.manual-file-actions button {
		border: none;
		padding: 0.5rem 0.85rem;
		border-radius: 0.5rem;
		background: rgba(63, 208, 139, 0.15);
		color: #aefcd5;
		cursor: pointer;
	}

</style>
