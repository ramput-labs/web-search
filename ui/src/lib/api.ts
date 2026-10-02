import type { Ask, Question, SystemOneResponse } from './types';

export class ApiError extends Error {}

function detail(body: unknown, status: number): string {
	if (body && typeof body === 'object' && 'detail' in body) {
		const d = (body as { detail: unknown }).detail;
		return typeof d === 'string' ? d : JSON.stringify(d);
	}
	return `Request failed (${status})`;
}

/** The id of the one question each ask becomes. */
export const ANSWER = 'answer';

/** Two or more options make a choice; none makes a yes-or-no question. */
export function toQuestion({ question, options }: Ask): Question {
	if (options.length < 2) return { type: 'noul', instructions: question };
	return {
		type: 'choice',
		instructions: question,
		criteria: Object.fromEntries(options.map((o) => [o, o]))
	};
}

export async function classify(
	ask: Ask,
	options: { webSearch: boolean; signal?: AbortSignal }
): Promise<SystemOneResponse> {
	const response = await fetch('/api/v1/systemone', {
		method: 'POST',
		headers: {
			'content-type': 'application/json',
			'x-web-search': options.webSearch ? 'always' : 'off'
		},
		body: JSON.stringify({
			state: ask.question,
			questions: { [ANSWER]: toQuestion(ask) }
		}),
		signal: options.signal
	});
	const body = await response.json().catch(() => null);
	if (!response.ok) throw new ApiError(detail(body, response.status));
	return body as SystemOneResponse;
}

export interface Health {
	server: boolean;
	kev: boolean;
	searxng: boolean;
}

export async function getHealth(): Promise<Health> {
	try {
		const response = await fetch('/api/health');
		if (!response.ok) return { server: false, kev: false, searxng: false };
		const body = await response.json();
		return { server: true, kev: !!body.kev, searxng: !!body.searxng };
	} catch {
		return { server: false, kev: false, searxng: false };
	}
}
