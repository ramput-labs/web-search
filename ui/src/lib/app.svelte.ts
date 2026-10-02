import { classify, getHealth, type Health } from './api';
import type { Ask, AssistantMessage, Chat } from './types';

// v2: messages carry a question and options instead of a classifier
const KEY = 'web-search-ui:v2';

interface Saved {
	chats: Chat[];
	webSearch: boolean;
}

export const uid = () => crypto.randomUUID();

function load(): Partial<Saved> {
	try {
		return JSON.parse(localStorage.getItem(KEY) ?? '{}');
	} catch {
		return {};
	}
}

class AppState {
	chats = $state<Chat[]>([]);
	chatId = $state<string | null>(null);
	webSearch = $state(true);
	health = $state<Health | null>(null);

	chat = $derived(this.chats.find((c) => c.id === this.chatId) ?? null);
	busy = $derived(
		this.chat?.messages.some((m) => m.role === 'assistant' && m.status === 'pending') ?? false
	);

	#controllers = new Map<string, AbortController>();

	init() {
		const saved = load();
		// a reload interrupts pending requests; they are shown as failed rather than spinning forever
		this.chats = (saved.chats ?? []).map((chat) => ({
			...chat,
			messages: chat.messages.map((m) =>
				m.role === 'assistant' && m.status === 'pending'
					? { ...m, status: 'error', error: 'Interrupted' }
					: m
			)
		}));
		this.webSearch = saved.webSearch ?? true;
	}

	async checkHealth() {
		this.health = await getHealth();
	}

	persist() {
		const saved: Saved = { chats: this.chats, webSearch: this.webSearch };
		try {
			localStorage.setItem(KEY, JSON.stringify(saved));
		} catch {
			// storage full or blocked: the session still works, it just is not remembered
		}
	}

	newChat() {
		this.chatId = null;
	}

	openChat(id: string) {
		this.chatId = id;
	}

	deleteChat(id: string) {
		this.chats = this.chats.filter((c) => c.id !== id);
		if (this.chatId === id) this.chatId = null;
		this.persist();
	}

	async send({ question, options }: Ask) {
		question = question.trim();
		options = [...new Set(options.map((o) => o.trim()).filter(Boolean))];
		if (!question || options.length === 1 || this.busy) return;

		let chat = this.chat;
		if (!chat) {
			this.chats.unshift({
				id: uid(),
				title: question.slice(0, 60),
				createdAt: Date.now(),
				messages: []
			});
			chat = this.chats[0];
			this.chatId = chat.id;
		}
		chat.messages.push({ id: uid(), role: 'user', question, options });
		await this.#ask(chat, { question, options });
	}

	async retry(messageId: string) {
		const chat = this.chat;
		if (!chat || this.busy) return;
		const i = chat.messages.findIndex((m) => m.id === messageId);
		const old = chat.messages[i];
		if (old?.role !== 'assistant') return;
		chat.messages.splice(i, 1);
		await this.#ask(chat, old.ask, i);
	}

	stop() {
		for (const controller of this.#controllers.values()) controller.abort();
	}

	async #ask(chat: Chat, ask: Ask, at = chat.messages.length) {
		const id = uid();
		chat.messages.splice(at, 0, {
			id,
			role: 'assistant',
			ask,
			webSearch: this.webSearch,
			status: 'pending'
		});
		this.persist();

		// re-read through the proxy so updates are reactive
		const message = () => chat.messages.find((m) => m.id === id) as AssistantMessage;
		const controller = new AbortController();
		this.#controllers.set(id, controller);
		const started = performance.now();
		try {
			message().response = await classify(ask, {
				webSearch: this.webSearch,
				signal: controller.signal
			});
			message().status = 'done';
		} catch (e) {
			message().status = 'error';
			if (!controller.signal.aborted) this.checkHealth();
			message().error = controller.signal.aborted
				? 'Stopped'
				: e instanceof Error
					? e.message
					: String(e);
		} finally {
			message().elapsedMs = performance.now() - started;
			this.#controllers.delete(id);
			this.persist();
		}
	}
}

export const app = new AppState();
