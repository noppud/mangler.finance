<script lang="ts">
	let billingCycle: 'monthly' | 'annual' = 'monthly';
</script>

<svelte:head>
	<title>Pricing | Mangler</title>
</svelte:head>

<section class="pricing">
	<div class="pricing__header">
		<h1>Pricing</h1>
		<p class="pricing__subtitle">Start for free. Upgrade to get the capacity that exactly matches your team's needs.</p>
	</div>

	<div class="pricing__cards">
		<article class="pricing__card">
			<div class="pricing__card-header">
				<h2>Free</h2>
				<p class="pricing__card-description">Perfect for trying out Mangler</p>
			</div>

			<div class="pricing__price">
				<span class="pricing__currency">$</span>
				<span class="pricing__amount">0</span>
				<span class="pricing__period">per month</span>
			</div>

			<p class="pricing__note">No credit card needed</p>

			<a href="/login" class="pricing__btn pricing__btn--secondary">Get Started</a>

			<div class="pricing__features">
				<h3>Free forever</h3>
				<ul>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						1 spreadsheet
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						100 LLM tokens
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Basic formula validation
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Community support
					</li>
				</ul>
			</div>
		</article>

		<article class="pricing__card pricing__card--featured">
			<div class="pricing__badge">Most Popular</div>
			<div class="pricing__card-header">
				<h2>Pro</h2>
				<p class="pricing__card-description">For teams that need more power</p>
			</div>

			<div class="pricing__price">
				<span class="pricing__currency">$</span>
				<span class="pricing__amount">19.99</span>
				<span class="pricing__period">per month</span>
			</div>

			<p class="pricing__note">Unlimited spreadsheets</p>

			<a href="/login" class="pricing__btn pricing__btn--primary">Get Started</a>

			<div class="pricing__features">
				<h3>Everything in Free, plus:</h3>
				<ul>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Unlimited spreadsheets
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						1,000 LLM tokens included
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						€0.10 per 1k tokens after
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Advanced AI analysis
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Priority support
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Real-time monitoring
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Chrome extension access
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						API access
					</li>
				</ul>
			</div>
		</article>

		<article class="pricing__card">
			<div class="pricing__card-header">
				<h2>Enterprise</h2>
				<p class="pricing__card-description">For large organizations</p>
			</div>

			<div class="pricing__price">
				<span class="pricing__amount pricing__amount--custom">Custom</span>
			</div>

			<p class="pricing__note">Tailored to your needs</p>

			<a href="mailto:enterprise@mangler.finance" class="pricing__btn pricing__btn--secondary">Contact Sales</a>

			<div class="pricing__features">
				<h3>Everything in Pro, plus:</h3>
				<ul>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Custom token packages
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Dedicated support
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						On-premise deployment
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Custom integrations
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						SLA guarantees
					</li>
					<li>
						<svg class="check" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
						</svg>
						Advanced security features
					</li>
				</ul>
			</div>
		</article>
	</div>

	<div class="pricing__faq">
		<h2>Frequently Asked Questions</h2>
		<div class="pricing__faq-grid">
			<div class="pricing__faq-item">
				<h3>What are LLM tokens?</h3>
				<p>LLM tokens are units of AI processing power used for analyzing and improving your spreadsheets. Each analysis consumes tokens based on complexity.</p>
			</div>
			<div class="pricing__faq-item">
				<h3>Can I upgrade or downgrade anytime?</h3>
				<p>Yes! You can change your plan at any time. Changes take effect immediately and are prorated.</p>
			</div>
			<div class="pricing__faq-item">
				<h3>What payment methods do you accept?</h3>
				<p>We accept all major credit cards, debit cards, and support payment via invoice for Enterprise customers.</p>
			</div>
			<div class="pricing__faq-item">
				<h3>Is there a setup fee?</h3>
				<p>No setup fees for any plan. Start using Mangler immediately after signing up.</p>
			</div>
		</div>
	</div>
</section>

<style>
	.pricing {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem 1.5rem 4rem;
	}

	.pricing__header {
		text-align: center;
		margin-bottom: 3rem;
	}

	.pricing__header h1 {
		font-size: clamp(2.4rem, 4vw, 3.6rem);
		margin: 0 0 1rem;
		color: #f6fff9;
		letter-spacing: -0.04em;
	}

	.pricing__subtitle {
		font-size: 1.1rem;
		color: rgba(221, 248, 237, 0.85);
		max-width: 50ch;
		margin: 0 auto;
		line-height: 1.6;
	}

	.pricing__cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		gap: 1.5rem;
		margin-bottom: 4rem;
	}

	.pricing__card {
		position: relative;
		padding: 2rem;
		border-radius: 1.5rem;
		background: rgba(4, 9, 8, 0.75);
		border: 1px solid rgba(82, 136, 117, 0.4);
		box-shadow: 0 25px 50px rgba(2, 5, 4, 0.65);
		display: flex;
		flex-direction: column;
	}

	.pricing__card--featured {
		border-color: rgba(78, 240, 178, 0.5);
		background: radial-gradient(circle at top, rgba(60, 236, 163, 0.08), transparent 60%),
			rgba(4, 9, 8, 0.85);
		transform: scale(1.05);
	}

	.pricing__badge {
		position: absolute;
		top: -12px;
		left: 50%;
		transform: translateX(-50%);
		padding: 0.35rem 1rem;
		border-radius: 999px;
		background: linear-gradient(135deg, #2de28c, #69fabc);
		color: #02150d;
		font-size: 0.8rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	.pricing__card-header {
		margin-bottom: 1.5rem;
	}

	.pricing__card-header h2 {
		margin: 0 0 0.5rem;
		font-size: 1.6rem;
		color: #f6fff9;
	}

	.pricing__card-description {
		margin: 0;
		color: rgba(211, 240, 230, 0.8);
		font-size: 0.95rem;
	}

	.pricing__price {
		display: flex;
		align-items: baseline;
		gap: 0.25rem;
		margin-bottom: 0.5rem;
	}

	.pricing__currency {
		font-size: 1.2rem;
		color: rgba(221, 248, 237, 0.6);
	}

	.pricing__amount {
		font-size: 2.8rem;
		font-weight: 700;
		color: #f6fff9;
		letter-spacing: -0.04em;
	}

	.pricing__amount--custom {
		font-size: 2.2rem;
	}

	.pricing__period {
		color: rgba(211, 240, 230, 0.6);
		font-size: 0.9rem;
		margin-left: 0.25rem;
	}

	.pricing__note {
		color: rgba(183, 246, 218, 0.7);
		font-size: 0.85rem;
		margin: 0 0 1.5rem;
		height: 1.2em;
	}

	.pricing__btn {
		display: inline-block;
		width: 100%;
		padding: 0.85rem 1.4rem;
		border-radius: 999px;
		border: 1px solid transparent;
		font-weight: 600;
		text-decoration: none;
		text-align: center;
		transition: transform 150ms ease, box-shadow 150ms ease;
		margin-bottom: 1.5rem;
	}

	.pricing__btn--primary {
		background: linear-gradient(135deg, #2de28c, #69fabc);
		color: #02150d;
		box-shadow: 0 20px 30px rgba(47, 226, 140, 0.3);
	}

	.pricing__btn--secondary {
		background: rgba(47, 226, 140, 0.12);
		color: #c2ffe7;
		border-color: rgba(47, 226, 140, 0.4);
	}

	.pricing__btn:hover {
		transform: translateY(-2px);
	}

	.pricing__features {
		flex-grow: 1;
	}

	.pricing__features h3 {
		font-size: 0.9rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: rgba(183, 246, 218, 0.6);
		margin: 0 0 1rem;
	}

	.pricing__features ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.pricing__features li {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.5rem 0;
		color: rgba(211, 240, 230, 0.85);
		font-size: 0.95rem;
		line-height: 1.5;
	}

	.check {
		color: #4ef0b2;
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.pricing__faq {
		padding-top: 2rem;
		border-top: 1px solid rgba(85, 193, 151, 0.25);
	}

	.pricing__faq h2 {
		text-align: center;
		font-size: clamp(1.8rem, 3vw, 2.4rem);
		margin: 0 0 2rem;
		color: #f6fff9;
	}

	.pricing__faq-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 2rem;
	}

	.pricing__faq-item h3 {
		margin: 0 0 0.5rem;
		font-size: 1.1rem;
		color: #f6fff9;
	}

	.pricing__faq-item p {
		margin: 0;
		color: rgba(211, 240, 230, 0.8);
		line-height: 1.6;
	}

	@media (max-width: 900px) {
		.pricing__cards {
			grid-template-columns: 1fr;
		}

		.pricing__card--featured {
			transform: none;
		}
	}
</style>