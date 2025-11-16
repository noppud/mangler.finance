<script lang="ts">
	// Sheet Mangler Chat component with tooltip
	import { onMount, onDestroy } from 'svelte';

	interface Message {
		id: string;
		role: 'user' | 'assistant' | 'tool';
		content?: string;
		metadata?: any;
	}

	interface Issue {
		cell_location: string;
		title: string;
		description?: string;
		severity: 'low' | 'medium' | 'high' | 'critical';
		category?: string;
		suggestedFix?: string;
		color: string;
	}

	let messages: Message[] = [];
	let inputText = '';
	let isLoading = false;
	let isTyping = false;
	let chatWindow: HTMLDivElement;
	let textarea: HTMLTextAreaElement;
	let sessionId: string | null = null;
	let spreadsheetUrl = '';
	let sheetTitle = 'Sheet1';
	let issues: Issue[] = [];
	let streamController: AbortController | null = null;

	function removeTypingPlaceholder() {
		const last = messages[messages.length - 1];
		if (last && last.role === 'assistant' && !last.content) {
			messages = messages.slice(0, -1);
		}
	}

	// Generate unique IDs
	function generateMessageId(): string {
		return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
	}

	function generateSessionId(): string {
		return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
	}

	// Auto-resize textarea
	function autoResize(element: HTMLTextAreaElement) {
		element.style.height = 'auto';
		element.style.height = element.scrollHeight + 'px';
	}

	// Scroll to bottom
	function scrollToBottom() {
		if (chatWindow) {
			chatWindow.scrollTop = chatWindow.scrollHeight;
		}
	}

	// Handle streaming response
	async function handleStreamResponse(response: Response) {
		const reader = response.body?.getReader();
		const decoder = new TextDecoder();

		if (!reader) {
			throw new Error('No response body');
		}

		let currentAssistantMessage: Message | null = null;
		let buffer = '';

		try {
			while (true) {
				const { done, value } = await reader.read();

				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');

				// Keep the last incomplete line in the buffer
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (line.startsWith('data: ')) {
						const data = line.slice(6);

						if (data === '[DONE]') {
							isTyping = false;
							continue;
						}

						try {
							const chunk = JSON.parse(data);

							switch (chunk.type) {
								case 'session':
									sessionId = chunk.sessionId;
									break;

								case 'content':
									if (!currentAssistantMessage) {
										const last = messages[messages.length - 1];
										if (last && last.role === 'assistant' && !last.content) {
											currentAssistantMessage = last;
											currentAssistantMessage.id = chunk.messageId || currentAssistantMessage.id;
											currentAssistantMessage.content = chunk.content;
											messages = [...messages.slice(0, -1), currentAssistantMessage];
										} else {
											currentAssistantMessage = {
												id: chunk.messageId || generateMessageId(),
												role: 'assistant',
												content: chunk.content
											};
											messages = [...messages, currentAssistantMessage];
										}
										isTyping = true;
									} else {
										currentAssistantMessage.content = (currentAssistantMessage.content || '') + chunk.content;
										// Trigger reactivity
										messages = messages;
									}
									scrollToBottom();
									break;

								case 'tool':
									if (chunk.metadata?.payload?.potential_errors) {
										issues = [...issues, ...chunk.metadata.payload.potential_errors];
									}
									break;

								case 'done':
									isTyping = false;
									break;

								case 'error':
									console.error('Stream error:', chunk.error);
									isTyping = false;
									break;
							}
						} catch (e) {
							console.error('Failed to parse chunk:', data, e);
						}
					}
				}
			}
		} finally {
			reader.releaseLock();
		}
	}

	// Send message
	async function sendMessage() {
		const text = inputText.trim();
		if (!text || isLoading) return;

		// Add user message
		const userMessage: Message = {
			id: generateMessageId(),
			role: 'user',
			content: text
		};
		messages = [...messages, userMessage];

		// Add placeholder assistant message for typing indicator
		const typingMessage: Message = {
			id: generateMessageId(),
			role: 'assistant',
			content: ''
		};
		messages = [...messages, typingMessage];

		// Clear input and show loading
		inputText = '';
		isLoading = true;
		isTyping = true;
		scrollToBottom();

		// Generate session ID if needed
		if (!sessionId) {
			sessionId = generateSessionId();
		}

		// Prepare request
		const request = {
			messages: [userMessage],
			sheetContext: spreadsheetUrl ? {
				spreadsheetId: spreadsheetUrl,
				sheetTitle: sheetTitle
			} : undefined,
			sessionId: sessionId
		};

		try {
			// Abort any existing stream
			if (streamController) {
				streamController.abort();
			}

			streamController = new AbortController();

			// Add timeout to prevent stuck state
			const timeoutId = setTimeout(() => {
				if (streamController) {
					streamController.abort();
					console.log('Request timeout after 30 seconds');
				}
			}, 30000);

			const response = await fetch('https://fintech-hackathon-production.up.railway.app/chat/stream', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(request),
				signal: streamController.signal
			});

			clearTimeout(timeoutId);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			await handleStreamResponse(response);
		} catch (error: any) {
			isTyping = false; // Ensure typing indicator is removed
			removeTypingPlaceholder();
			if (error.name === 'AbortError') {
				console.log('Stream aborted');
				// Add a user-friendly message for timeout
				messages = [...messages, {
					id: generateMessageId(),
					role: 'assistant',
					content: 'Request timed out. Please try again.'
				}];
			} else {
				console.error('Chat error:', error);
				messages = [...messages, {
					id: generateMessageId(),
					role: 'assistant',
					content: `Error: ${error.message || 'Failed to send message'}`
				}];
			}
		} finally {
			isLoading = false;
			isTyping = false;
			removeTypingPlaceholder();
			streamController = null;
		}
	}

	// Handle Enter key
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}

	// Handle issue actions
	function fixIssue(issue: Issue) {
		// Send a message to fix the issue
		inputText = `Fix this issue:\n\nLocation: ${issue.cell_location}\nSeverity: ${issue.severity}\nIssue: ${issue.title}\nDescription: ${issue.description || ''}\n${issue.suggestedFix ? `Suggested fix: ${issue.suggestedFix}` : ''}\n\nPlease use the update_cells tool to apply the appropriate fix for this issue.`;
		sendMessage();
	}

	function ignoreIssue(issue: Issue) {
		// Remove from issues list
		issues = issues.filter(i => i !== issue);
	}

	// Initialize
	onMount(() => {
		// Add welcome message
		messages = [{
			id: generateMessageId(),
			role: 'assistant',
			content: "Hi, I'm your Sheet Mangler assistant.\n\nI can help you analyze spreadsheets, detect issues, and apply fixes. Enter a Google Sheets URL above to get started, or just ask me questions about spreadsheet analysis."
		}];

		// Focus textarea
		if (textarea) {
			textarea.focus();
		}
	});

	// Cleanup
	onDestroy(() => {
		if (streamController) {
			streamController.abort();
		}
	});
</script>

<svelte:head>
	<title>Sheet Mangler Chat</title>
</svelte:head>

<div class="sheet-layout">
	<aside class="sheet-sidebar">
		<div class="sheet-card sheet-card--context">
			<p class="eyebrow">Sheet context</p>
			<div class="sheet-card__header-with-tooltip">
				<h2>Sheet Mangler</h2>
				<div class="tooltip-wrapper">
					<svg class="info-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
						<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
					</svg>
					<div class="tooltip-content">
						<h4>Step 1: Share Your Google Sheet</h4>
						<p>First, share your Google Sheet with our service account so we can install the extension.</p>
						<div class="service-account-section">
							<label>Service Account Email:</label>
							<div class="email-copy-box">
								<code>googlesheetworker@fintech-hackathon-476313.iam.gserviceaccount.com</code>
								<button class="copy-btn" on:click={() => {
									navigator.clipboard.writeText('googlesheetworker@fintech-hackathon-476313.iam.gserviceaccount.com');
								}}>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
										<path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
									</svg>
								</button>
							</div>
							<p class="permission-note">Copy this email and share your sheet with Editor permissions</p>
						</div>
					</div>
				</div>
			</div>
			<p>Attach a Google Sheet and Mangler will keep anomalies, formula drifts, and privacy leaks in check.</p>
			<label class="field">
				<span>Google Sheets URL</span>
				<input
					type="text"
					placeholder="Enter URL (optional)"
					bind:value={spreadsheetUrl}
					class="text-input"
				/>
			</label>
			<label class="field">
				<span>Sheet name</span>
				<input
					type="text"
					placeholder="Sheet1"
					bind:value={sheetTitle}
					class="text-input"
				/>
			</label>
		</div>

		<div class="sheet-card sheet-card--tips">
			<p class="eyebrow">Rapid playbook</p>
			<ul class="sheet-checklist">
				<li>Drop a Sheets link so Mangler can stream structure + metadata.</li>
				<li>Ask about anomalies, reconciliations, or formula guardrails.</li>
				<li>Let the assistant patch the sheet via update_cells when ready.</li>
			</ul>
		</div>

		<div class="sheet-card sheet-card--issues">
			<div class="sheet-card__header">
				<h3>Detected issues</h3>
				<span class="pill">{issues.length} open</span>
			</div>
			{#if issues.length > 0}
				<ul class="issues-list">
					{#each issues as issue}
						<li class="issue-card issue-severity-{issue.severity}" style="border-left-color: {issue.color}">
							<div class="issue-header">
								<span class="issue-location">{issue.cell_location}</span>
								<span class={`issue-chip issue-chip--${issue.severity}`}>
									{issue.severity}
								</span>
							</div>
							<div class="issue-title">{issue.title}</div>
							{#if issue.description}
								<div class="issue-description">{issue.description}</div>
							{/if}
							{#if issue.suggestedFix}
								<div class="issue-suggested-fix">
									<strong>Suggested fix:</strong> {issue.suggestedFix}
								</div>
							{/if}
							<div class="issue-actions">
								<button class="issue-btn issue-btn-fix" on:click={() => fixIssue(issue)} disabled={isLoading}>
									Fix with AI
								</button>
								<button class="issue-btn issue-btn-ignore" on:click={() => ignoreIssue(issue)}>
									Dismiss
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="empty-state">No issues yet—ask Mangler to audit your data and they'll appear here.</p>
			{/if}
		</div>
	</aside>

	<section class="sheet-chat">
		<header class="sheet-chat__header">
			<div>
				<p class="eyebrow">Worksheet assistant</p>
				<h1>Ask Mangler anything</h1>
				<p class="muted">Diagnose formulas, reconcile ledgers, or let Mangler write fix-ready instructions.</p>
			</div>
			<div class="sheet-status">
				<span class="dot dot--online" aria-hidden="true"></span>
				Live assistance
			</div>
		</header>

		<div class="sheet-chat__window" bind:this={chatWindow}>
			{#each messages as message}
				<div class="chat-row chat-row--{message.role}">
					<div class="chat-bubble chat-bubble--{message.role}">
						{#if message.role === 'assistant' && isTyping && message === messages[messages.length - 1] && !message.content}
							<div class="typing-dots">
								<span></span>
								<span></span>
								<span></span>
							</div>
						{:else}
							{message.content || ''}
						{/if}
					</div>
				</div>
			{/each}
		</div>

		<div class="sheet-composer">
			<textarea
				bind:this={textarea}
				bind:value={inputText}
				on:keydown={handleKeydown}
				on:input={() => autoResize(textarea)}
				placeholder="Ask about this sheet, formulas, or issues..."
				disabled={isLoading}
				rows="1"
			/>
			<button on:click={sendMessage} disabled={!inputText.trim() || isLoading} class="send-btn">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2 .01 7z"/>
				</svg>
			</button>
		</div>
	</section>
</div>

<style>
	.sheet-layout {
		display: grid;
		grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
		gap: 1.75rem;
		height: calc(100vh - 180px);
		max-height: calc(100vh - 180px);
		position: relative;
	}

	.sheet-sidebar {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		overflow-y: auto;
		overflow-x: visible;
		padding-right: 0.5rem;
		position: relative;
		z-index: 2;
		scrollbar-width: none;
	}

	.sheet-sidebar::-webkit-scrollbar {
		width: 0;
		height: 0;
	}

	.sheet-sidebar::-webkit-scrollbar-thumb {
		background: transparent;
		border-radius: 0;
	}

	.sheet-card {
		padding: 1.6rem;
		border-radius: 1.4rem;
		background: rgba(5, 11, 9, 0.82);
		border: 1px solid rgba(80, 134, 115, 0.4);
		box-shadow: 0 18px 35px rgba(0, 0, 0, 0.55);
	}

	.sheet-card--context {
		background: radial-gradient(circle at top right, rgba(60, 236, 163, 0.16), transparent 55%),
			linear-gradient(135deg, rgba(5, 12, 10, 0.95), rgba(8, 18, 15, 0.9));
	}

	.sheet-card--tips {
		background: rgba(6, 12, 10, 0.7);
	}

	.sheet-card--issues {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.sheet-card__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.eyebrow {
		text-transform: uppercase;
		letter-spacing: 0.28em;
		font-size: 0.75rem;
		color: rgba(184, 224, 213, 0.68);
		margin: 0 0 0.35rem;
	}

	.sheet-card h2 {
		margin: 0 0 0.5rem;
		font-size: 1.6rem;
	}

	.sheet-card p {
		margin: 0;
		color: rgba(212, 239, 229, 0.85);
		line-height: 1.6;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		margin-top: 1rem;
		font-size: 0.9rem;
		color: rgba(211, 239, 229, 0.9);
	}

	.text-input {
		padding: 0.65rem 0.75rem;
		border-radius: 0.8rem;
		border: 1px solid rgba(102, 146, 133, 0.5);
		background: rgba(3, 8, 6, 0.7);
		color: #effff8;
		font-size: 0.95rem;
		transition: border-color 0.2s ease, box-shadow 0.2s ease;
	}

	.text-input:focus {
		outline: none;
		border-color: #52f1b3;
		box-shadow: 0 0 0 2px rgba(82, 241, 179, 0.15);
	}

	.sheet-checklist {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.7rem;
	}

	.sheet-checklist li {
		position: relative;
		padding-left: 1.5rem;
		font-size: 0.9rem;
		color: rgba(204, 230, 220, 0.85);
	}

	.sheet-checklist li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0.35rem;
		width: 0.65rem;
		height: 0.65rem;
		border-radius: 50%;
		background: linear-gradient(135deg, #29dd8f, #65ffd3);
		box-shadow: 0 0 10px rgba(101, 255, 211, 0.6);
	}

	.sheet-chat {
		padding: 1.8rem;
		border-radius: 1.6rem;
		background: rgba(5, 10, 9, 0.85);
		border: 1px solid rgba(84, 141, 122, 0.4);
		box-shadow: 0 35px 55px rgba(0, 0, 0, 0.55);
		height: 100%;
		overflow: hidden;
		position: relative;
		z-index: 1;
	}

	.sheet-chat__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1.5rem;
		padding-bottom: 1.25rem;
		border-bottom: 1px solid rgba(72, 110, 99, 0.35);
	}

	.sheet-chat__header h1 {
		margin: 0.35rem 0 0.4rem;
		font-size: 2rem;
	}

	.sheet-status {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0.9rem;
		border-radius: 999px;
		background: rgba(48, 191, 133, 0.15);
		border: 1px solid rgba(48, 191, 133, 0.45);
		font-size: 0.85rem;
		color: #c8ffe8;
	}

	.sheet-chat__window {
		flex: 1;
		margin: 1.5rem 0;
		padding: 1.25rem;
		border-radius: 1.25rem;
		background: rgba(3, 8, 6, 0.75);
		border: 1px solid rgba(60, 90, 81, 0.45);
		overflow-y: auto;
		overflow-x: hidden;
		max-height: calc(100vh - 400px);
		min-height: 300px;
	}

	.sheet-chat__window::-webkit-scrollbar {
		width: 6px;
	}

	.sheet-chat__window::-webkit-scrollbar-thumb {
		background: rgba(84, 141, 122, 0.6);
		border-radius: 3px;
	}

	.chat-row {
		display: flex;
		margin-bottom: 1rem;
	}

	.chat-row--user {
		justify-content: flex-end;
	}

	.chat-row--assistant {
		justify-content: flex-start;
	}

	.chat-bubble {
		max-width: 70%;
		padding: 0.9rem 1.1rem;
		border-radius: 1.1rem;
		white-space: pre-wrap;
		line-height: 1.6;
		font-size: 0.95rem;
	}

	.chat-bubble--user {
		background: linear-gradient(135deg, #30e294, #66ffd0);
		color: #032015;
		box-shadow: 0 12px 25px rgba(48, 226, 148, 0.3);
		border-bottom-right-radius: 0.35rem;
	}

	.chat-bubble--assistant {
		background: rgba(20, 35, 30, 0.85);
		border: 1px solid rgba(67, 103, 92, 0.55);
		color: #e0f6ec;
		border-bottom-left-radius: 0.35rem;
	}

	.typing-dots {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.typing-dots span {
		width: 8px;
		height: 8px;
		background: #6b9984;
		border-radius: 50%;
		animation: typing-jump 1.2s infinite ease-in-out;
	}

	.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
	.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

	@keyframes typing-jump {
		0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
		40% { transform: translateY(-4px); opacity: 1; }
	}

	.issues-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		flex: 1;
		overflow-y: auto;
	}

	.issues-list::-webkit-scrollbar {
		width: 4px;
	}

	.issue-card {
		padding: 1rem;
		border-radius: 1rem;
		background: rgba(4, 9, 7, 0.85);
		border: 1px solid rgba(69, 109, 96, 0.45);
		border-left: 4px solid;
		transition: transform 0.2s ease, background 0.2s ease;
	}

	.issue-card:hover {
		transform: translateX(4px);
		background: rgba(4, 9, 7, 0.95);
	}

	.issue-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.85rem;
		margin-bottom: 0.4rem;
	}

	.issue-location {
		font-weight: 600;
	}

	.issue-title {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 0.35rem;
	}

	.issue-description {
		font-size: 0.9rem;
		color: rgba(201, 230, 219, 0.9);
		margin-bottom: 0.75rem;
		line-height: 1.5;
	}

	.issue-suggested-fix {
		background: rgba(47, 226, 140, 0.1);
		border-left: 2px solid rgba(47, 226, 140, 0.6);
		padding: 0.5rem;
		border-radius: 0.5rem;
		font-size: 0.85rem;
		margin-bottom: 0.75rem;
	}

	.issue-actions {
		display: flex;
		gap: 0.5rem;
	}

	.issue-btn {
		flex: 1;
		padding: 0.55rem 1rem;
		border-radius: 0.75rem;
		border: none;
		font-size: 0.85rem;
		font-weight: 600;
		cursor: pointer;
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}

	.issue-btn-fix {
		background: linear-gradient(135deg, #30e294, #66ffd0);
		color: #032015;
		box-shadow: 0 8px 18px rgba(48, 226, 148, 0.25);
	}

	.issue-btn-ignore {
		background: rgba(80, 128, 112, 0.3);
		color: #cfe7de;
		border: 1px solid rgba(80, 128, 112, 0.6);
	}

	.issue-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.issue-chip {
		padding: 0.15rem 0.65rem;
		border-radius: 999px;
		font-size: 0.75rem;
		text-transform: capitalize;
		letter-spacing: 0.1em;
	}

	.issue-chip--critical { background: rgba(255, 71, 84, 0.2); color: #ffbdc3; }
	.issue-chip--high { background: rgba(255, 153, 0, 0.2); color: #ffd9a3; }
	.issue-chip--medium { background: rgba(255, 255, 0, 0.15); color: #fff7bf; }
	.issue-chip--low { background: rgba(64, 232, 173, 0.15); color: #d4ffef; }

	.empty-state {
		margin: 1rem 0 0;
		color: rgba(202, 229, 217, 0.75);
	}

	.sheet-composer {
		display: flex;
		gap: 0.85rem;
		align-items: flex-end;
		padding-top: 1rem;
		border-top: 1px solid rgba(72, 110, 99, 0.35);
	}

	.sheet-composer textarea {
		flex: 1;
		padding: 0.85rem 1rem;
		border-radius: 1rem;
		border: 1px solid rgba(78, 124, 111, 0.6);
		background: rgba(3, 8, 6, 0.85);
		color: #f1fff7;
		font-size: 1rem;
		font-family: inherit;
		resize: none;
		max-height: 120px;
		line-height: 1.5;
		overflow-y: auto;
		overflow-x: hidden;
		transition: border-color 0.2s ease, box-shadow 0.2s ease;
		scrollbar-width: thin;
		scrollbar-color: rgba(78, 124, 111, 0.4) transparent;
	}

	.sheet-composer textarea::-webkit-scrollbar {
		width: 4px;
	}

	.sheet-composer textarea::-webkit-scrollbar-thumb {
		background: rgba(78, 124, 111, 0.4);
		border-radius: 2px;
	}

	.sheet-composer textarea::-webkit-scrollbar-track {
		background: transparent;
	}

	.sheet-composer textarea:focus {
		outline: none;
		border-color: #4ef0b2;
		box-shadow: 0 0 0 2px rgba(78, 240, 178, 0.2);
	}

	.send-btn {
		width: 48px;
		height: 48px;
		border-radius: 1.1rem;
		border: none;
		background: linear-gradient(135deg, #30e294, #66ffd0);
		color: #032015;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 12px 24px rgba(48, 226, 148, 0.35);
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}

	.send-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		box-shadow: none;
	}

	.send-btn:not(:disabled):hover {
		transform: translateY(-1px);
	}

	.pill {
		padding: 0.25rem 0.9rem;
		border-radius: 999px;
		border: 1px solid rgba(215, 255, 237, 0.3);
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.2em;
		color: rgba(215, 255, 237, 0.85);
	}

	.muted {
		margin: 0;
		color: rgba(205, 229, 219, 0.72);
	}

	.dot {
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 50%;
	}

	.dot--online {
		background: #4ef0b2;
		box-shadow: 0 0 10px rgba(78, 240, 178, 0.7);
	}

	/* Tooltip styles */
	.sheet-card__header-with-tooltip {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.sheet-card__header-with-tooltip h2 {
		margin: 0;
	}

	.tooltip-wrapper {
		position: relative;
		display: inline-flex;
		align-items: center;
	}

	.info-icon {
		color: rgba(184, 224, 213, 0.68);
		cursor: help;
		transition: color 0.2s ease;
	}

	.tooltip-wrapper:hover .info-icon {
		color: #4ef0b2;
	}

	.tooltip-content {
		position: absolute;
		left: 30px;
		top: -10px;
		width: 380px;
		max-width: min(380px, 80vw);
		padding: 1.25rem;
		background: rgba(3, 8, 7, 0.98);
		border: 1px solid rgba(78, 240, 178, 0.4);
		border-radius: 1rem;
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(78, 240, 178, 0.1);
		z-index: 10000;
		opacity: 0;
		visibility: hidden;
		transform: translateX(-10px);
		transition: opacity 0.3s ease, visibility 0.3s ease, transform 0.3s ease;
		pointer-events: none;
	}

	.tooltip-wrapper:hover .tooltip-content {
		opacity: 1;
		visibility: visible;
		transform: translateX(0);
		pointer-events: auto;
	}

	.tooltip-content h4 {
		margin: 0 0 0.75rem;
		font-size: 1.1rem;
		color: #f6fff9;
	}

	.tooltip-content p {
		margin: 0 0 1rem;
		color: rgba(212, 239, 229, 0.9);
		line-height: 1.5;
		font-size: 0.9rem;
	}

	.service-account-section {
		background: rgba(6, 14, 12, 0.7);
		border: 1px solid rgba(72, 110, 99, 0.5);
		border-radius: 0.75rem;
		padding: 1rem;
	}

	.service-account-section label {
		display: block;
		font-size: 0.85rem;
		color: rgba(184, 224, 213, 0.8);
		margin-bottom: 0.5rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	.email-copy-box {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: rgba(3, 8, 6, 0.9);
		border: 1px solid rgba(78, 240, 178, 0.3);
		border-radius: 0.5rem;
		padding: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.email-copy-box code {
		flex: 1;
		font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
		font-size: 0.8rem;
		color: #4ef0b2;
		word-break: break-all;
		background: transparent;
	}

	.copy-btn {
		padding: 0.4rem;
		background: rgba(78, 240, 178, 0.15);
		border: 1px solid rgba(78, 240, 178, 0.4);
		border-radius: 0.4rem;
		color: #4ef0b2;
		cursor: pointer;
		transition: background 0.2s ease, transform 0.2s ease;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.copy-btn:hover {
		background: rgba(78, 240, 178, 0.25);
		transform: scale(1.05);
	}

	.copy-btn:active {
		transform: scale(0.95);
	}

	.permission-note {
		margin: 0;
		font-size: 0.85rem;
		color: rgba(202, 229, 217, 0.85);
		font-style: italic;
	}

	@media (max-width: 960px) {
		.sheet-layout {
			grid-template-columns: 1fr;
		}

		.sheet-chat {
			order: -1;
		}

		.sheet-chat__header {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>
