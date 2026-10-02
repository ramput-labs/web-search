<script lang="ts">
	import { app } from '#lib/app.svelte.ts';
	import Icon from './Icon.svelte';

	let { open = $bindable(true) }: { open?: boolean } = $props();

	const mobile = () => matchMedia('(max-width: 768px)').matches;
	const close = () => {
		if (mobile()) open = false;
	};

	const groups = $derived.by(() => {
		// eslint-disable-next-line svelte/prefer-svelte-reactivity -- read once per render of the list
		const today = new Date().setHours(0, 0, 0, 0);
		const week = today - 6 * 864e5;
		const out: { label: string; chats: typeof app.chats }[] = [
			{ label: 'Today', chats: [] },
			{ label: 'Previous 7 days', chats: [] },
			{ label: 'Older', chats: [] }
		];
		for (const chat of app.chats) {
			out[chat.createdAt >= today ? 0 : chat.createdAt >= week ? 1 : 2].chats.push(chat);
		}
		return out.filter((g) => g.chats.length);
	});

	const status = $derived.by(() => {
		const h = app.health;
		if (!h) return { tone: 'idle', text: 'Connecting…' };
		if (!h.server) return { tone: 'down', text: 'Server offline' };
		if (!h.kev) return { tone: 'down', text: 'Model offline' };
		if (!h.searxng) return { tone: 'warn', text: 'Web search offline' };
		return { tone: 'up', text: 'All systems online' };
	});
</script>

{#if open}
	<button class="scrim" onclick={() => (open = false)} aria-label="Close sidebar"></button>
{/if}

<aside class:open aria-label="Chats">
	<div class="inner">
		<div class="top">
			<button
				class="icon"
				onclick={() => (open = false)}
				aria-label="Close sidebar"
				title="Close sidebar"
			>
				<Icon name="sidebar" size={20} />
			</button>
			<button
				class="icon"
				onclick={() => {
					app.newChat();
					close();
				}}
				aria-label="New chat"
				title="New chat"
			>
				<Icon name="compose" size={19} />
			</button>
		</div>

		<button
			class="row brand"
			onclick={() => {
				app.newChat();
				close();
			}}
		>
			<span class="logo">D</span>
			<span>DECISION-4B</span>
		</button>

		<nav>
			{#each groups as group (group.label)}
				<p class="group">{group.label}</p>
				{#each group.chats as chat (chat.id)}
					<div class="chat" class:active={chat.id === app.chatId}>
						<button
							class="chat-title"
							onclick={() => {
								app.openChat(chat.id);
								close();
							}}
							aria-current={chat.id === app.chatId ? 'page' : undefined}>{chat.title}</button
						>
						<button
							class="delete"
							onclick={() => app.deleteChat(chat.id)}
							aria-label="Delete chat"
							title="Delete"
						>
							<Icon name="trash" size={15} />
						</button>
					</div>
				{/each}
			{/each}
		</nav>

		<button class="status" onclick={() => app.checkHealth()} title="Check again">
			<span class="dot {status.tone}"></span>
			{status.text}
		</button>
	</div>
</aside>

<style>
	aside {
		flex: none;
		width: 0;
		overflow: hidden;
		background: var(--sidebar);
		transition: width 0.2s ease;
	}
	aside.open {
		width: 260px;
	}
	.inner {
		display: flex;
		flex-direction: column;
		width: 260px;
		height: 100%;
		padding: 8px;
	}
	.top {
		display: flex;
		justify-content: space-between;
		padding-bottom: 8px;
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
		background: var(--surface-3);
		color: var(--text);
	}
	.row {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 8px 10px;
		border: 0;
		border-radius: 10px;
		background: none;
		color: var(--text);
		font: inherit;
		font-size: 14px;
		font-weight: 500;
		text-align: left;
		cursor: pointer;
	}
	.row:hover {
		background: var(--surface-3);
	}
	.logo {
		display: grid;
		place-items: center;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--text);
		color: var(--bg);
		font-size: 12px;
		font-weight: 700;
	}
	nav {
		flex: 1;
		overflow-y: auto;
		margin: 8px -8px 0;
		padding: 0 8px;
	}
	.group {
		margin: 18px 10px 6px;
		font-size: 12px;
		font-weight: 500;
		color: var(--text-3);
	}
	.chat {
		display: flex;
		align-items: center;
		border-radius: 10px;
	}
	.chat:hover,
	.chat.active {
		background: var(--surface-3);
	}
	.chat-title {
		flex: 1;
		min-width: 0;
		padding: 8px 10px;
		border: 0;
		background: none;
		color: var(--text);
		font: inherit;
		font-size: 14px;
		text-align: left;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		cursor: pointer;
	}
	.delete {
		display: grid;
		place-items: center;
		width: 28px;
		height: 28px;
		margin-right: 4px;
		border: 0;
		border-radius: 7px;
		background: none;
		color: var(--text-3);
		cursor: pointer;
		opacity: 0;
	}
	.chat:hover .delete,
	.chat.active .delete,
	.delete:focus-visible {
		opacity: 1;
	}
	.delete:hover {
		color: var(--low);
	}
	.status {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 8px;
		padding: 10px;
		border: 0;
		border-radius: 10px;
		background: none;
		color: var(--text-2);
		font: inherit;
		font-size: 13px;
		text-align: left;
		cursor: pointer;
	}
	.status:hover {
		background: var(--surface-3);
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--text-3);
	}
	.dot.up {
		background: var(--high);
	}
	.dot.warn {
		background: var(--mid);
	}
	.dot.down {
		background: var(--low);
	}
	.scrim {
		display: none;
	}
	@media (max-width: 768px) {
		aside {
			position: fixed;
			inset: 0 auto 0 0;
			z-index: 40;
		}
		aside.open {
			box-shadow: var(--shadow-lg);
		}
		.scrim {
			display: block;
			position: fixed;
			inset: 0;
			z-index: 39;
			border: 0;
			background: rgb(0 0 0 / 0.4);
		}
		.delete {
			opacity: 1;
		}
	}
</style>
