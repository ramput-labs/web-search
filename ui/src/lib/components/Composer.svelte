<script lang="ts">
	import { app } from '#lib/app.svelte.ts';
	import Icon from './Icon.svelte';

	let {
		question = $bindable(''),
		options = $bindable<string[]>([])
	}: { question?: string; options?: string[] } = $props();

	let textarea: HTMLTextAreaElement;
	let draft = $state('');

	export function focus() {
		textarea?.focus();
	}

	/** The options as they would be sent, including one still being typed. */
	const all = $derived([...new Set([...options, draft].map((o) => o.trim()).filter(Boolean))]);
	const ready = $derived(!!question.trim() && all.length !== 1 && !app.busy);
	const hint = $derived(
		all.length === 0
			? 'Yes / no answer'
			: all.length === 1
				? 'Add one more option'
				: `${all.length} options`
	);

	function add(text: string) {
		const parts = text
			.split(/[,\n]/)
			.map((p) => p.trim())
			.filter(Boolean);
		options = [...new Set([...options, ...parts])];
	}

	function submit() {
		if (!ready) return;
		app.send({ question, options: all });
		question = '';
		options = [];
		draft = '';
		focus();
	}

	function onQuestionKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
			e.preventDefault();
			submit();
		}
	}

	function onOptionKey(e: KeyboardEvent) {
		if (e.isComposing) return;
		if ((e.key === 'Enter' || e.key === ',') && draft.trim()) {
			e.preventDefault();
			add(draft);
			draft = '';
		} else if (e.key === 'Enter') {
			e.preventDefault();
			submit();
		} else if (e.key === 'Backspace' && !draft && options.length) {
			draft = options.at(-1) ?? '';
			options = options.slice(0, -1);
			e.preventDefault();
		}
	}

	function onpaste(e: ClipboardEvent) {
		const text = e.clipboardData?.getData('text') ?? '';
		if (/[,\n]/.test(text)) {
			e.preventDefault();
			add(draft + text);
			draft = '';
		}
	}
</script>

<form
	class="composer"
	onsubmit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<textarea
		bind:this={textarea}
		bind:value={question}
		onkeydown={onQuestionKey}
		rows="1"
		placeholder="Ask a question"
		aria-label="Question"></textarea>

	<div class="options">
		<span class="options-label">Options</span>
		<ul>
			{#each options as option, i (option)}
				<li class="chip">
					<span>{option}</span>
					<button
						type="button"
						onclick={() => (options = options.filter((_, j) => j !== i))}
						aria-label="Remove {option}"><Icon name="close" size={12} /></button
					>
				</li>
			{/each}
			<li class="grow">
				<input
					bind:value={draft}
					onkeydown={onOptionKey}
					onblur={() => {
						if (draft.trim()) {
							add(draft);
							draft = '';
						}
					}}
					{onpaste}
					placeholder={options.length
						? 'Add another'
						: 'Type an option, press Enter. Empty for yes / no'}
					aria-label="Add an option"
				/>
			</li>
		</ul>
	</div>

	<div class="bar">
		<button
			type="button"
			class="pill"
			class:on={app.webSearch}
			aria-pressed={app.webSearch}
			title={app.webSearch
				? 'DECISION-4B searches the web before answering'
				: 'DECISION-4B answers without searching'}
			onclick={() => {
				app.webSearch = !app.webSearch;
				app.persist();
			}}
		>
			<Icon name="globe" size={16} />
			<span>Search</span>
		</button>

		<span class="hint" class:warn={all.length === 1}>{hint}</span>

		{#if app.busy}
			<button type="button" class="send" onclick={() => app.stop()} aria-label="Stop" title="Stop">
				<Icon name="stop" size={14} />
			</button>
		{:else}
			<button type="submit" class="send" disabled={!ready} aria-label="Ask" title="Ask">
				<Icon name="send" size={18} />
			</button>
		{/if}
	</div>
</form>

<style>
	.composer {
		display: flex;
		flex-direction: column;
		padding: 10px 10px 10px 12px;
		border-radius: 28px;
		background: var(--surface);
		box-shadow: var(--shadow);
	}
	textarea {
		field-sizing: content;
		min-height: 44px;
		max-height: 200px;
		padding: 8px 8px 4px;
		border: 0;
		outline: 0;
		resize: none;
		background: none;
		color: var(--text);
		font: inherit;
		font-size: 16px;
		line-height: 1.5;
	}
	textarea::placeholder,
	input::placeholder {
		color: var(--text-3);
	}
	.options {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		margin: 2px 8px 8px;
		padding-top: 10px;
		border-top: 1px solid var(--border);
	}
	.options-label {
		flex: none;
		padding-top: 5px;
		font-size: 13px;
		font-weight: 500;
		color: var(--text-3);
	}
	ul {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		flex: 1;
		min-width: 0;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		max-width: 100%;
		height: 30px;
		padding: 0 4px 0 12px;
		border-radius: 999px;
		background: var(--surface-2);
		font-size: 14px;
		animation: pop 0.12s ease-out;
	}
	.chip span {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.chip button {
		display: grid;
		place-items: center;
		width: 22px;
		height: 22px;
		border: 0;
		border-radius: 50%;
		background: none;
		color: var(--text-3);
		cursor: pointer;
	}
	.chip button:hover {
		background: var(--surface-3);
		color: var(--text);
	}
	.grow {
		flex: 1;
		min-width: 140px;
	}
	input {
		width: 100%;
		height: 30px;
		padding: 0 2px;
		border: 0;
		outline: 0;
		background: none;
		color: var(--text);
		font: inherit;
		font-size: 14px;
	}
	.bar {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 36px;
		padding: 0 14px 0 12px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: none;
		color: var(--text-2);
		font: inherit;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		transition:
			background 0.15s,
			color 0.15s,
			border-color 0.15s;
	}
	.pill:hover {
		background: var(--surface-2);
		color: var(--text);
	}
	.pill.on {
		border-color: var(--text);
		background: var(--text);
		color: var(--bg);
	}
	.hint {
		margin-left: auto;
		font-size: 13px;
		color: var(--text-3);
		white-space: nowrap;
	}
	.hint.warn {
		color: var(--mid);
	}
	.send {
		display: grid;
		place-items: center;
		flex: none;
		width: 36px;
		height: 36px;
		border: 0;
		border-radius: 50%;
		background: var(--text);
		color: var(--bg);
		cursor: pointer;
		transition:
			opacity 0.15s,
			transform 0.1s;
	}
	.send:active:not(:disabled) {
		transform: scale(0.94);
	}
	.send:disabled {
		background: var(--surface-3);
		color: var(--text-3);
		cursor: default;
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: scale(0.9);
		}
	}
</style>
