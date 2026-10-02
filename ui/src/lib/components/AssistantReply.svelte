<script lang="ts">
	import { ANSWER, toQuestion } from '#lib/api.ts';
	import { app } from '#lib/app.svelte.ts';
	import { seconds } from '#lib/format.ts';
	import type { AssistantMessage, ChoiceAnswer } from '#lib/types.ts';
	import AnswerCard from './AnswerCard.svelte';
	import Icon from './Icon.svelte';
	import Sources from './Sources.svelte';

	let { message }: { message: AssistantMessage } = $props();

	const search = $derived(message.response?.search);
	const question = $derived(toQuestion(message.ask));
	const answer = $derived(message.response?.answers[ANSWER]);
	// what a source passage should be about: the question, and for a choice the option picked
	const about = $derived(
		`${message.ask.question} ${answer?.type === 'choice' ? (answer as ChoiceAnswer).choice : ''}`
	);
	const tokens = $derived(
		Object.values(message.response?.usage ?? {}).reduce<number>(
			(sum, n) => sum + (typeof n === 'number' ? n : 0),
			0
		)
	);

	const STOPPED: Record<string, string> = {
		no_new_results: 'Web search found nothing new',
		search_unavailable: 'Web search is unavailable right now',
		max_evidence: 'Reached the source limit'
	};
	const stopped = $derived.by(() => {
		const reason = search?.stopped;
		if (!reason) return null;
		if (reason.startsWith('kev_error_'))
			return `The model rejected the search results (${reason.slice(10)})`;
		return STOPPED[reason] ?? reason;
	});

	let raw = $state(false);
	let copied = $state(false);
	async function copy() {
		await navigator.clipboard.writeText(JSON.stringify(message.response, null, 2));
		copied = true;
		setTimeout(() => (copied = false), 1500);
	}
</script>

<div class="reply">
	{#if message.status === 'pending'}
		<div class="pending" role="status">
			<span class="pulse"></span>
			<span class="shimmer">{message.webSearch ? 'Searching the web' : 'Classifying'}</span>
		</div>
	{:else if message.status === 'error'}
		<div class="error" role="alert">
			<span>{message.error}</span>
			<button onclick={() => app.retry(message.id)} disabled={app.busy}
				><Icon name="retry" size={14} /> Try again</button
			>
		</div>
	{:else if message.response}
		{#if search?.evidence.length}
			<Sources evidence={search.evidence} {about} />
		{/if}

		{#if stopped}
			<p class="notice">
				{stopped}{#if search?.unresponsive_engines.length}<span>
						({search.unresponsive_engines.join(', ')})</span
					>{/if}
			</p>
		{/if}

		{#if answer}
			<AnswerCard
				{question}
				{answer}
				report={search?.questions[ANSWER]}
				threshold={search?.threshold}
			/>
		{/if}

		{#if raw}
			<pre>{JSON.stringify(message.response, null, 2)}</pre>
		{/if}

		<div class="actions">
			<button onclick={copy} aria-label="Copy JSON" title={copied ? 'Copied' : 'Copy JSON'}>
				<Icon name={copied ? 'check' : 'copy'} size={16} />
			</button>
			<button
				onclick={() => (raw = !raw)}
				class:on={raw}
				aria-label="Raw response"
				title="Raw response"
			>
				<Icon name="code" size={16} />
			</button>
			<button
				onclick={() => app.retry(message.id)}
				disabled={app.busy}
				aria-label="Ask again"
				title="Ask again"
			>
				<Icon name="retry" size={16} />
			</button>
			<span class="stats">
				{seconds(message.elapsedMs)}{#if tokens}&nbsp;· {tokens.toLocaleString()}
					tokens{/if}{#if !message.webSearch}&nbsp;· search off{/if}
			</span>
		</div>
	{/if}
</div>

<style>
	.reply {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.pending {
		display: flex;
		align-items: center;
		gap: 12px;
		min-height: 28px;
		font-size: 15px;
	}
	.pulse {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: var(--text);
		animation: pulse 1.2s ease-in-out infinite;
	}
	.shimmer {
		color: transparent;
		background: linear-gradient(90deg, var(--text-3) 30%, var(--text) 50%, var(--text-3) 70%);
		background-size: 200% 100%;
		background-clip: text;
		-webkit-background-clip: text;
		animation: shimmer 1.8s linear infinite;
	}
	.error {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 14px;
		border-radius: 14px;
		background: var(--low-bg);
		color: var(--low);
		font-size: 14px;
	}
	.error span {
		flex: 1;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.error button {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		flex: none;
		height: 32px;
		padding: 0 12px;
		border: 0;
		border-radius: 999px;
		background: var(--text);
		color: var(--bg);
		font: inherit;
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
	}
	.notice {
		margin: 10px 0 0;
		font-size: 13px;
		color: var(--mid);
	}
	.notice span {
		color: var(--text-3);
	}
	pre {
		margin: 4px 0 8px;
		padding: 14px 16px;
		max-height: 380px;
		overflow: auto;
		border-radius: 14px;
		background: var(--surface-2);
		font-size: 12.5px;
		line-height: 1.55;
	}
	.actions {
		display: flex;
		align-items: center;
		gap: 2px;
		margin-left: -6px;
	}
	.actions button {
		display: grid;
		place-items: center;
		width: 32px;
		height: 32px;
		border: 0;
		border-radius: 8px;
		background: none;
		color: var(--text-3);
		cursor: pointer;
	}
	.actions button:hover:not(:disabled),
	.actions button.on {
		background: var(--surface-2);
		color: var(--text);
	}
	.actions button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.stats {
		margin-left: 8px;
		font-size: 12.5px;
		color: var(--text-3);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	@keyframes pulse {
		50% {
			transform: scale(0.7);
			opacity: 0.5;
		}
	}
	@keyframes shimmer {
		from {
			background-position: 100% 0;
		}
		to {
			background-position: -100% 0;
		}
	}
</style>
