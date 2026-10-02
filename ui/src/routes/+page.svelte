<script lang="ts">
	import { app } from '#lib/app.svelte.ts';
	import AssistantReply from '#lib/components/AssistantReply.svelte';
	import Composer from '#lib/components/Composer.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Sidebar from '#lib/components/Sidebar.svelte';
	import ThemeSelect from '#lib/components/ThemeSelect.svelte';
	import { EXAMPLES } from '#lib/presets.ts';
	import { theme } from '#lib/theme.svelte.ts';
	import { onMount, tick } from 'svelte';

	app.init();

	let sidebar = $state(typeof window !== 'undefined' && window.innerWidth > 768);
	let question = $state('');
	let options = $state<string[]>([]);
	let composer = $state<Composer>();
	let scroller = $state<HTMLElement>();

	onMount(() => {
		app.checkHealth();
		theme.init();
	});

	// follow the conversation as replies arrive
	$effect(() => {
		const last = app.chat?.messages.at(-1);
		void (last?.role === 'assistant' && last.status);
		void app.chat?.messages.length;
		tick().then(() => scroller?.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' }));
	});

	function example(e: (typeof EXAMPLES)[number]) {
		question = e.question;
		options = [...e.options];
		composer?.focus();
	}
	const offline = $derived(app.health && (!app.health.server || !app.health.kev));
</script>

<svelte:window
	onfocus={() => app.checkHealth()}
	onkeydown={(e) => {
		if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'o') {
			e.preventDefault();
			app.newChat();
		}
	}}
/>

<svelte:head>
	<title>{app.chat ? `${app.chat.title} · DECISION-4B` : 'DECISION-4B'}</title>
</svelte:head>

<div class="shell">
	<Sidebar bind:open={sidebar} />

	<main>
		<header>
			{#if !sidebar}
				<button
					class="icon"
					onclick={() => (sidebar = true)}
					aria-label="Open sidebar"
					title="Open sidebar"
				>
					<Icon name="sidebar" size={20} />
				</button>
				<button
					class="icon"
					onclick={() => app.newChat()}
					aria-label="New chat"
					title="New chat (⇧⌘O)"
				>
					<Icon name="compose" size={19} />
				</button>
			{/if}
			<span class="name">DECISION-4B</span>
			<span class="spacer"></span>
			<ThemeSelect />
		</header>

		{#if app.chat}
			<div class="scroll" bind:this={scroller}>
				<div class="thread">
					{#each app.chat.messages as message (message.id)}
						{#if message.role === 'user'}
							<div class="user">
								<div class="bubble">
									<p>{message.question}</p>
									<ul aria-label="Options">
										{#if message.options.length}
											{#each message.options as option (option)}<li>{option}</li>{/each}
										{:else}
											<li>Yes</li>
											<li>No</li>
										{/if}
									</ul>
								</div>
							</div>
						{:else}
							<AssistantReply {message} />
						{/if}
					{/each}
				</div>
			</div>
		{/if}

		<div class="dock" class:welcome={!app.chat}>
			{#if !app.chat}
				<h1>What do you want to know?</h1>
			{/if}
			{#if offline}
				<p class="offline" role="status">
					{app.health?.server ? "Can't reach the model." : "Can't reach the server."} Start it with
					<code>make dev</code>, then
					<button onclick={() => app.checkHealth()}>check again</button>.
				</p>
			{/if}
			<Composer bind:this={composer} bind:question bind:options />
			{#if app.chat}
				<p class="fineprint">
					DECISION-4B can be wrong. Web results are untrusted, so check important answers.
				</p>
			{:else}
				<ul class="examples">
					{#each EXAMPLES as e (e.question)}
						<li>
							<button onclick={() => example(e)}>{e.question}</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</main>
</div>

<style>
	.shell {
		display: flex;
		height: 100dvh;
	}
	main {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-width: 0;
	}
	header {
		display: flex;
		align-items: center;
		gap: 2px;
		height: 56px;
		padding: 0 10px;
		flex: none;
	}
	.icon {
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
	.icon:hover {
		background: var(--surface-2);
		color: var(--text);
	}
	.name {
		margin-left: 6px;
		padding: 6px 4px;
		font-size: 17px;
		font-weight: 700;
		letter-spacing: 0.01em;
	}
	.spacer {
		flex: 1;
	}
	.scroll {
		flex: 1;
		overflow-y: auto;
	}
	.thread,
	.dock {
		width: 100%;
		max-width: 768px;
		margin: 0 auto;
		padding: 0 20px;
	}
	.thread {
		display: flex;
		flex-direction: column;
		gap: 32px;
		padding-top: 16px;
		padding-bottom: 40px;
	}
	.user {
		display: flex;
		justify-content: flex-end;
	}
	.bubble {
		max-width: 70%;
		padding: 10px 18px 12px;
		border-radius: 22px;
		background: var(--surface-2);
	}
	.bubble p {
		margin: 0;
		font-size: 15.5px;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.bubble ul {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin: 8px 0 0;
		padding: 0;
		list-style: none;
	}
	.bubble li {
		padding: 2px 10px;
		border-radius: 999px;
		background: var(--bg);
		color: var(--text-2);
		font-size: 13px;
	}
	.dock {
		flex: none;
		padding-bottom: max(12px, env(safe-area-inset-bottom));
	}
	.dock.welcome {
		display: flex;
		flex-direction: column;
		justify-content: center;
		flex: 1;
		gap: 28px;
		padding-bottom: 14vh;
	}
	h1 {
		margin: 0;
		text-align: center;
		font-size: clamp(24px, 4vw, 28px);
		font-weight: 500;
		letter-spacing: -0.01em;
	}
	.offline {
		margin: 0 0 10px;
		padding: 10px 14px;
		border-radius: 14px;
		background: var(--low-bg);
		color: var(--low);
		font-size: 14px;
		text-align: center;
	}
	.offline code {
		font-size: 13px;
	}
	.offline button {
		padding: 0;
		border: 0;
		background: none;
		color: inherit;
		font: inherit;
		text-decoration: underline;
		cursor: pointer;
	}
	.welcome .offline {
		margin: -12px 0 -12px;
	}
	.fineprint {
		margin: 10px 0 0;
		text-align: center;
		font-size: 12px;
		color: var(--text-3);
	}
	.examples {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 8px;
		margin: -8px 0 0;
		padding: 0;
		list-style: none;
	}
	.examples button {
		width: 100%;
		height: 100%;
		padding: 10px 16px;
		border: 1px solid var(--border);
		border-radius: 16px;
		text-align: left;
		background: none;
		color: var(--text-2);
		font: inherit;
		font-size: 14px;
		cursor: pointer;
		transition:
			background 0.15s,
			color 0.15s;
	}
	.examples button:hover {
		background: var(--surface-2);
		color: var(--text);
	}
	@media (max-width: 600px) {
		.examples {
			grid-template-columns: 1fr;
		}
		.bubble {
			max-width: 85%;
		}
	}
</style>
