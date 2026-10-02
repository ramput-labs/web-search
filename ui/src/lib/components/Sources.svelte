<script lang="ts">
	import { highlightUrl, reference } from '#lib/fragment.ts';
	import { domain } from '#lib/format.ts';
	import type { Evidence } from '#lib/types.ts';
	import Icon from './Icon.svelte';

	/** `about`: the question and the chosen answer, which pick the passage to highlight in each source. */
	let { evidence, about = '' }: { evidence: Evidence[]; about?: string } = $props();

	let expanded = $state(false);
	const PREVIEW = 4;
	const sources = $derived(
		evidence.map((source) => {
			const ref = reference(source.content, about);
			return { ...source, ref, href: highlightUrl(source.url, ref) };
		})
	);
	const shown = $derived(sources.slice(0, PREVIEW));
	const hidden = $derived(sources.slice(PREVIEW));
	const favicon = (url: string) => `https://icons.duckduckgo.com/ip3/${domain(url)}.ico`;
	const hide = (e: Event) => ((e.currentTarget as HTMLImageElement).style.visibility = 'hidden');
</script>

<section aria-label="Sources">
	<div class="tags">
		{#each shown as source, i (source.url || i)}
			<a
				class="tag"
				href={source.href}
				target="_blank"
				rel="noopener noreferrer"
				title={source.ref ? `“${source.ref.passage}”` : source.title}
			>
				<img src={favicon(source.url)} alt="" loading="lazy" onerror={hide} />
				<span class="domain">{domain(source.url)}</span>
				<span class="n">{i + 1}</span>
			</a>
		{/each}
		{#if sources.length}
			<button class="tag more" onclick={() => (expanded = !expanded)} aria-expanded={expanded}>
				{#if !expanded && hidden.length}
					<span class="stack">
						{#each hidden.slice(0, 3) as source, i (i)}<img
								src={favicon(source.url)}
								alt=""
								loading="lazy"
								onerror={hide}
							/>{/each}
					</span>
					+{hidden.length} · References
				{:else}
					{expanded ? 'Hide references' : 'References'}
				{/if}
			</button>
		{/if}
	</div>

	{#if expanded}
		<div class="refs">
			<p class="refs-note">
				The text the model read from each page. Open one to see the <mark>highlighted</mark> passage on
				the site.
			</p>
			<ol>
				{#each sources as source, i (source.url || i)}
					<li>
						<a href={source.href} target="_blank" rel="noopener noreferrer">
							<span class="list-head">
								<span class="n">{i + 1}</span>
								<img src={favicon(source.url)} alt="" loading="lazy" onerror={hide} />
								<span class="domain">{domain(source.url)}</span>
								<span class="open"
									>{source.ref ? 'Open and highlight' : 'Open'}
									<Icon name="external" size={12} /></span
								>
							</span>
							<span class="title">{source.title || domain(source.url)}</span>
							{#if source.ref}
								<blockquote>
									{source.ref.before}<mark>{source.ref.passage}</mark>{source.ref.after}
								</blockquote>
							{:else if source.content}
								<blockquote>{source.content}</blockquote>
							{/if}
						</a>
					</li>
				{/each}
			</ol>
		</div>
	{/if}
</section>

<style>
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.tag {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		max-width: 220px;
		height: 30px;
		padding: 0 6px 0 9px;
		border: 0;
		border-radius: 999px;
		background: var(--surface-2);
		color: var(--text-2);
		font: inherit;
		font-size: 13px;
		text-decoration: none;
		cursor: pointer;
		transition:
			background 0.15s,
			color 0.15s;
	}
	.tag:hover {
		background: var(--surface-3);
		color: var(--text);
	}
	.more {
		padding: 0 11px 0 9px;
	}
	img {
		width: 14px;
		height: 14px;
		border-radius: 3px;
		flex: none;
	}
	.stack {
		display: flex;
	}
	.stack img {
		margin-left: -4px;
		border-radius: 50%;
		box-shadow: 0 0 0 1.5px var(--surface-2);
	}
	.stack img:first-child {
		margin-left: 0;
	}
	.domain {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.n {
		display: grid;
		place-items: center;
		flex: none;
		min-width: 18px;
		height: 18px;
		padding: 0 5px;
		border-radius: 9px;
		background: var(--surface-3);
		color: var(--text-2);
		font-size: 11px;
		font-weight: 500;
		font-variant-numeric: tabular-nums;
	}
	.tag:hover .n {
		background: var(--bg);
	}
	.refs {
		margin-top: 12px;
	}
	.refs-note {
		margin: 0 0 6px;
		font-size: 12.5px;
		color: var(--text-3);
	}
	ol {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	ol a {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin: 0 -12px;
		padding: 10px 12px;
		border-radius: 12px;
		color: inherit;
		text-decoration: none;
	}
	ol a:hover {
		background: var(--surface-2);
	}
	.list-head {
		display: flex;
		align-items: center;
		gap: 7px;
		font-size: 12px;
		color: var(--text-3);
	}
	.open {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		margin-left: auto;
		opacity: 0;
		transition: opacity 0.15s;
	}
	ol a:hover .open,
	ol a:focus-visible .open {
		opacity: 1;
		color: var(--text-2);
	}
	.title {
		font-size: 14px;
		font-weight: 500;
	}
	blockquote {
		margin: 2px 0 0;
		padding-left: 12px;
		border-left: 2px solid var(--border-strong);
		font-size: 13.5px;
		line-height: 1.55;
		color: var(--text-3);
	}
	mark {
		padding: 1px 0;
		border-radius: 3px;
		background: var(--mark);
		color: var(--text);
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	@media (hover: none) {
		.open {
			opacity: 1;
		}
	}
</style>
