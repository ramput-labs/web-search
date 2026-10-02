<script lang="ts">
	import { theme, type Theme } from '#lib/theme.svelte.ts';
	import Icon, { type IconName } from './Icon.svelte';

	const OPTIONS: { value: Theme; label: string; icon: IconName }[] = [
		{ value: 'light', label: 'Light', icon: 'sun' },
		{ value: 'dark', label: 'Dark', icon: 'moon' },
		{ value: 'system', label: 'System', icon: 'monitor' }
	];

	let open = $state(false);
	const current = $derived(OPTIONS.find((o) => o.value === theme.value) ?? OPTIONS[2]);

	function pick(value: Theme) {
		theme.set(value);
		open = false;
	}
</script>

<svelte:window
	onclick={() => (open = false)}
	onkeydown={(e) => {
		if (e.key === 'Escape') open = false;
	}}
/>

<div class="theme">
	<button
		class="trigger"
		onclick={(e) => {
			e.stopPropagation();
			open = !open;
		}}
		aria-haspopup="menu"
		aria-expanded={open}
		aria-label="Theme: {current.label}"
		title="Theme"
	>
		<Icon name={current.icon} size={18} />
	</button>

	{#if open}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="menu" role="menu" tabindex="-1" onclick={(e) => e.stopPropagation()}>
			{#each OPTIONS as option (option.value)}
				<button
					role="menuitemradio"
					aria-checked={theme.value === option.value}
					onclick={() => pick(option.value)}
				>
					<Icon name={option.icon} size={16} />
					<span>{option.label}</span>
					{#if theme.value === option.value}<span class="check"
							><Icon name="check" size={16} /></span
						>{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.theme {
		position: relative;
	}
	.trigger {
		display: grid;
		place-items: center;
		width: 36px;
		height: 36px;
		border: 0;
		border-radius: 8px;
		background: none;
		color: var(--text-2);
		cursor: pointer;
	}
	.trigger:hover,
	.trigger[aria-expanded='true'] {
		background: var(--surface-2);
		color: var(--text);
	}
	.menu {
		position: absolute;
		top: calc(100% + 6px);
		right: 0;
		z-index: 30;
		width: 168px;
		padding: 6px;
		border-radius: 14px;
		background: var(--surface);
		box-shadow: var(--shadow-lg);
		animation: pop 0.12s ease-out;
	}
	.menu button {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 8px 10px;
		border: 0;
		border-radius: 9px;
		background: none;
		color: var(--text);
		font: inherit;
		font-size: 14px;
		text-align: left;
		cursor: pointer;
	}
	.menu button:hover {
		background: var(--surface-2);
	}
	.menu button :global(svg) {
		color: var(--text-2);
	}
	.check {
		display: grid;
		margin-left: auto;
	}
	.check :global(svg) {
		color: var(--text) !important;
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
	}
</style>
