<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';

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
										currentAssistantMessage = {
											id: chunk.messageId || generateMessageId(),
											role: 'assistant',
											content: chunk.content
										};
										messages = [...messages, currentAssistantMessage];
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

			const response = await fetch('https://fintech-hackathon-production.up.railway.app/chat/stream', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(request),
				signal: streamController.signal
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			await handleStreamResponse(response);
		} catch (error: any) {
			if (error.name === 'AbortError') {
				console.log('Stream aborted');
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

<div class="chat-container">
	<!-- Header -->
	<div class="chat-header">
		<h1>Sheet Mangler</h1>
		<div class="sheet-input">
			<input
				type="text"
				placeholder="Enter Google Sheets URL (optional)"
				bind:value={spreadsheetUrl}
				class="url-input"
			/>
			<input
				type="text"
				placeholder="Sheet name"
				bind:value={sheetTitle}
				class="sheet-input-field"
			/>
		</div>
	</div>

	<!-- Chat window -->
	<div class="chat-window" bind:this={chatWindow}>
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

		<!-- Issues -->
		{#if issues.length > 0}
			<div class="issues-section">
				<h3>Detected Issues</h3>
				{#each issues as issue}
					<div class="issue-card issue-severity-{issue.severity}" style="border-left-color: {issue.color}">
						<div class="issue-header">
							<span class="issue-location">{issue.cell_location}</span>
							<span class="issue-severity">{issue.severity}</span>
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
							<button
								class="issue-btn issue-btn-fix"
								on:click={() => fixIssue(issue)}
								disabled={isLoading}
							>
								Fix with AI
							</button>
							<button
								class="issue-btn issue-btn-ignore"
								on:click={() => ignoreIssue(issue)}
							>
								Ignore
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Input area -->
	<div class="input-area">
		<textarea
			bind:this={textarea}
			bind:value={inputText}
			on:keydown={handleKeydown}
			on:input={() => autoResize(textarea)}
			placeholder="Ask about this sheet, formulas, or issues..."
			disabled={isLoading}
			rows="1"
		/>
		<button
			on:click={sendMessage}
			disabled={!inputText.trim() || isLoading}
			class="send-btn"
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
				<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2 .01 7z"/>
			</svg>
		</button>
	</div>
</div>

<style>
	.chat-container {
		display: flex;
		flex-direction: column;
		height: 100vh;
		background: #0a0f0d;
		color: #e0f2e9;
	}

	.chat-header {
		padding: 1.5rem;
		background: linear-gradient(135deg, rgba(15, 32, 28, 0.95), rgba(28, 50, 44, 0.85));
		border-bottom: 1px solid rgba(82, 110, 100, 0.4);
	}

	.chat-header h1 {
		margin: 0 0 1rem 0;
		font-size: 1.5rem;
		color: #f3fff9;
	}

	.sheet-input {
		display: flex;
		gap: 0.5rem;
	}

	.url-input {
		flex: 1;
	}

	.sheet-input-field {
		width: 150px;
	}

	.url-input, .sheet-input-field {
		padding: 0.5rem;
		background: rgba(5, 12, 10, 0.6);
		border: 1px solid rgba(82, 110, 100, 0.6);
		border-radius: 0.5rem;
		color: #e0f2e9;
		font-size: 0.9rem;
	}

	.url-input::placeholder, .sheet-input-field::placeholder {
		color: rgba(181, 214, 201, 0.5);
	}

	.chat-window {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
		background: #0a0f0d;
	}

	.chat-window::-webkit-scrollbar {
		width: 6px;
	}

	.chat-window::-webkit-scrollbar-track {
		background: transparent;
	}

	.chat-window::-webkit-scrollbar-thumb {
		background: rgba(82, 110, 100, 0.6);
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
		padding: 0.75rem 1rem;
		border-radius: 1rem;
		white-space: pre-wrap;
		word-wrap: break-word;
		line-height: 1.5;
	}

	.chat-bubble--user {
		background: linear-gradient(135deg, #2ba36a, #3fd08b);
		color: #04130d;
		border-bottom-right-radius: 0.25rem;
	}

	.chat-bubble--assistant {
		background: rgba(28, 50, 44, 0.6);
		color: #e0f2e9;
		border: 1px solid rgba(82, 110, 100, 0.3);
		border-bottom-left-radius: 0.25rem;
	}

	/* Typing indicator */
	.typing-dots {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 4px 0;
	}

	.typing-dots span {
		width: 8px;
		height: 8px;
		background: #6b9984;
		border-radius: 50%;
		animation: typing-jump 1.2s infinite ease-in-out;
	}

	.typing-dots span:nth-child(1) {
		animation-delay: 0s;
	}

	.typing-dots span:nth-child(2) {
		animation-delay: 0.2s;
	}

	.typing-dots span:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes typing-jump {
		0%, 80%, 100% {
			transform: translateY(0);
			opacity: 0.4;
		}
		40% {
			transform: translateY(-4px);
			opacity: 1;
		}
	}

	/* Issues section */
	.issues-section {
		margin: 2rem 0;
		padding: 1.5rem;
		background: rgba(28, 50, 44, 0.3);
		border-radius: 1rem;
		border: 1px solid rgba(82, 110, 100, 0.4);
	}

	.issues-section h3 {
		margin: 0 0 1rem 0;
		color: #f3fff9;
		font-size: 1.1rem;
	}

	.issue-card {
		background: rgba(5, 12, 10, 0.8);
		border-radius: 0.75rem;
		padding: 1rem;
		margin-bottom: 1rem;
		border-left: 3px solid;
		transition: all 0.2s ease;
	}

	.issue-card:hover {
		background: rgba(5, 12, 10, 1);
	}

	.issue-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.issue-location {
		background: rgba(82, 110, 100, 0.3);
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.85rem;
		font-family: monospace;
	}

	.issue-severity {
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.issue-severity-critical {
		background: rgba(220, 38, 38, 0.2);
		color: #fca5a5;
	}

	.issue-severity-high {
		background: rgba(251, 146, 60, 0.2);
		color: #fdba74;
	}

	.issue-severity-medium {
		background: rgba(250, 204, 21, 0.2);
		color: #fde047;
	}

	.issue-severity-low {
		background: rgba(59, 130, 246, 0.2);
		color: #93bbfc;
	}

	.issue-title {
		font-weight: 500;
		margin-bottom: 0.5rem;
		color: #f3fff9;
	}

	.issue-description {
		font-size: 0.9rem;
		color: rgba(181, 214, 201, 0.85);
		margin-bottom: 0.75rem;
		line-height: 1.5;
	}

	.issue-suggested-fix {
		background: rgba(43, 163, 106, 0.1);
		border-left: 2px solid #2ba36a;
		padding: 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.85rem;
		margin-bottom: 1rem;
		color: #a7f3d0;
	}

	.issue-actions {
		display: flex;
		gap: 0.5rem;
	}

	.issue-btn {
		flex: 1;
		padding: 0.5rem 1rem;
		border-radius: 0.5rem;
		border: none;
		font-size: 0.85rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.issue-btn-fix {
		background: linear-gradient(135deg, #2ba36a, #3fd08b);
		color: #04130d;
	}

	.issue-btn-fix:hover:not(:disabled) {
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(63, 208, 139, 0.3);
	}

	.issue-btn-ignore {
		background: rgba(82, 110, 100, 0.3);
		color: #b5d6c9;
		border: 1px solid rgba(82, 110, 100, 0.6);
	}

	.issue-btn-ignore:hover {
		background: rgba(82, 110, 100, 0.5);
	}

	.issue-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Input area */
	.input-area {
		display: flex;
		gap: 0.75rem;
		padding: 1.5rem;
		background: linear-gradient(135deg, rgba(15, 32, 28, 0.95), rgba(28, 50, 44, 0.85));
		border-top: 1px solid rgba(82, 110, 100, 0.4);
	}

	textarea {
		flex: 1;
		padding: 0.75rem;
		background: rgba(5, 12, 10, 0.8);
		border: 1px solid rgba(82, 110, 100, 0.6);
		border-radius: 0.75rem;
		color: #e0f2e9;
		font-size: 0.95rem;
		font-family: inherit;
		resize: none;
		max-height: 150px;
		line-height: 1.5;
		transition: all 0.2s ease;
	}

	textarea::placeholder {
		color: rgba(181, 214, 201, 0.5);
	}

	textarea:focus {
		outline: none;
		border-color: #2ba36a;
		background: rgba(5, 12, 10, 1);
		box-shadow: 0 0 0 2px rgba(43, 163, 106, 0.1);
	}

	textarea:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.send-btn {
		width: 42px;
		height: 42px;
		border-radius: 0.75rem;
		border: none;
		background: transparent;
		color: #6b9984;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
		flex-shrink: 0;
		align-self: flex-end;
	}

	.send-btn:not(:disabled):hover {
		background: rgba(43, 163, 106, 0.1);
		color: #2ba36a;
	}

	.send-btn:not(:disabled) {
		color: #2ba36a;
	}

	.send-btn:disabled {
		color: rgba(107, 153, 132, 0.4);
		cursor: not-allowed;
	}
</style>