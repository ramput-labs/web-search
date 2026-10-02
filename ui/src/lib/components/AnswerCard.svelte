<script lang="ts">
	import { humanize, percent, tier, TIER_LABEL } from '#lib/format.ts';
	import type {
		Answer,
		ChoiceAnswer,
		NoulAnswer,
		OtherAnswer,
		Question,
		QuestionReport
	} from '#lib/types.ts';
	import Icon from './Icon.svelte';

	let {
		question,
		answer,
		report,
		threshold = 0.5
	}: { question: Question; answer: Answer; report?: QuestionReport; threshold?: number } = $props();

	interface Row {
		label: string;
		description?: string;
		p: number;
	}

	function describe(key: string, description: string | undefined) {
		// options typed by the user are their own label; only machine ids need humanizing
		const label = description ?? humanize(key);
		return {
			label,
			description:
				description && description.toLowerCase() !== label.toLowerCase() ? description : undefined
		};
	}

	const view = $derived.by(() => {
		if (answer.type === 'choice') {
			const a = answer as ChoiceAnswer;
			const rows: Row[] = Object.entries(a.probabilities)
				.map(([key, p]) => ({ ...describe(key, question.criteria?.[key]), p }))
				.sort((x, y) => y.p - x.p);
			return {
				rows,
				confidence: a.confidence,
				...describe(a.choice, question.criteria?.[a.choice])
			};
		}
		if (answer.type === 'noul') {
			const p = (answer as NoulAnswer).noul;
			const rows: Row[] = [
				{ label: 'Yes', p },
				{ label: 'No', p: 1 - p }
			].sort((x, y) => y.p - x.p);
			return {
				rows,
				confidence: Math.abs(2 * p - 1),
				label: p >= 0.5 ? 'Yes' : 'No',
				description: undefined
			};
		}
		const confidence = Number((answer as OtherAnswer).confidence ?? 0);
		return { rows: [] as Row[], confidence, label: humanize(answer.type), description: undefined };
	});

	const level = $derived(tier(view.confidence, threshold));
	let open = $state(false);
</script>

<div class="answer">
	<div class="verdict">
		<div class="label">
			<strong>{view.label}</strong>
			{#if view.description}<span>{view.description}</span>{/if}
		</div>
		<span
			class="badge {level}"
			title="DECISION-4B's confidence; below {percent(threshold)} it searches the web"
		>
			{TIER_LABEL[level]} · {percent(view.confidence)}
		</span>
	</div>

	<div class="meter" aria-hidden="true">
		<div class="fill {level}" style:width={percent(view.confidence)}></div>
	</div>

	{#if report?.searched || report?.needs_review || view.rows.length > 1}
		<div class="meta">
			{#if report?.searched}
				<span title={report.query ? `Searched for: ${report.query}` : undefined}>
					<Icon name="globe" size={13} /> Searched the web · {percent(report.initial_confidence)} → {percent(
						report.confidence
					)}
				</span>
			{/if}
			{#if report?.needs_review}
				<span class="review"><Icon name="alert" size={13} /> Needs review</span>
			{/if}
			{#if view.rows.length > 1}
				<button class="toggle" class:open onclick={() => (open = !open)} aria-expanded={open}>
					{open ? 'Hide' : 'All'} options <Icon name="chevron" size={14} />
				</button>
			{/if}
		</div>
	{/if}

	{#if open}
		<ul class="rows">
			{#each view.rows as row, i (row.label)}
				<li class:top={i === 0}>
					<span class="row-label"
						>{row.label}{#if row.description}<em>{row.description}</em>{/if}</span
					>
					<span class="bar"><span style:width={percent(row.p)}></span></span>
					<span class="p">{percent(row.p)}</span>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.answer {
		padding: 4px 0 12px;
	}
	.verdict {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}
	.label {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 2px 10px;
		min-width: 0;
	}
	.label strong {
		font-size: 22px;
		font-weight: 700;
		letter-spacing: -0.01em;
		line-height: 1.25;
	}
	.label span {
		font-size: 15px;
		color: var(--text-2);
	}
	.badge {
		flex: none;
		padding: 4px 10px;
		border-radius: 999px;
		font-size: 13px;
		font-weight: 500;
		font-variant-numeric: tabular-nums;
	}
	.badge.high {
		color: var(--high);
		background: var(--high-bg);
	}
	.badge.mid {
		color: var(--mid);
		background: var(--mid-bg);
	}
	.badge.low {
		color: var(--low);
		background: var(--low-bg);
	}
	.meter {
		height: 4px;
		margin-top: 12px;
		border-radius: 2px;
		background: var(--surface-2);
		overflow: hidden;
	}
	.fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
	}
	.fill.high {
		background: var(--high);
	}
	.fill.mid {
		background: var(--mid);
	}
	.fill.low {
		background: var(--low);
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px 14px;
		margin-top: 10px;
		font-size: 13px;
		color: var(--text-3);
	}
	.meta > span {
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	.review {
		color: var(--low);
	}
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		margin-left: auto;
		padding: 2px 4px;
		border: 0;
		border-radius: 6px;
		background: none;
		color: var(--text-2);
		font: inherit;
		cursor: pointer;
	}
	.toggle:hover {
		color: var(--text);
	}
	.toggle :global(svg) {
		transition: transform 0.15s;
	}
	.toggle.open :global(svg) {
		transform: rotate(180deg);
	}
	.rows {
		display: grid;
		grid-template-columns: minmax(0, auto) minmax(80px, 1fr) 40px;
		align-items: center;
		gap: 10px 14px;
		margin: 14px 0 0;
		padding: 0;
		list-style: none;
	}
	.rows li {
		display: contents;
	}
	.row-label {
		font-size: 14px;
		color: var(--text-2);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.row-label em {
		margin-left: 8px;
		font-style: normal;
		color: var(--text-3);
	}
	.top .row-label {
		color: var(--text);
		font-weight: 500;
	}
	.bar {
		height: 6px;
		border-radius: 3px;
		background: var(--surface-2);
		overflow: hidden;
	}
	.bar span {
		display: block;
		height: 100%;
		border-radius: 3px;
		background: var(--text-3);
	}
	.top .bar span {
		background: var(--text);
	}
	.p {
		font-size: 13px;
		text-align: right;
		color: var(--text-2);
		font-variant-numeric: tabular-nums;
	}
	@media (max-width: 520px) {
		.rows {
			grid-template-columns: minmax(0, 1fr) 70px 36px;
		}
		.row-label em {
			display: none;
		}
	}
</style>
