/// <reference types="bun" />
import { describe, expect, test } from 'bun:test';
import { highlightUrl, reference } from './fragment.ts';

// snippets as SearXNG returned them
const WIKI =
	'Canberra (/ ˈkænbrə / ⓘ KAN-brə; Ngunawal: Kanbarra) is the capital city of Australia and the largest population centre in the Australian Capital Territory. With an estimated population of 484,630 as of 2025, Canberra is';
const LIST =
	'The capital of Australia is Canberra, which is also the seat of the national government. The web page lists the eight capital cities of the states and territories, their populations, and their establishment dates.';

describe('reference', () => {
	test('skips bracketed pronunciations and the word cut off at the end', () => {
		expect(reference(WIKI)?.passage).toBe(
			'is the capital city of Australia and the largest population centre in the Australian Capital Territory.'
		);
	});

	test('prefers the sentence about the question over the longest one', () => {
		expect(reference(LIST, 'What is the capital of Australia? Canberra')?.passage).toBe(
			'The capital of Australia is Canberra, which is also the seat of the national government.'
		);
	});

	test('keeps quotes out of the words that must match exactly', () => {
		const ref = reference(
			'At OpenAI\'s DevDay event on Tuesday, the company announced the launch of Dots, a new personal agentic assistant powered by GPT-6 Astra. The company describes Dots as "remarkably capable ...'
		);
		expect(ref?.passage.startsWith('DevDay event on Tuesday')).toBe(true);
	});

	test('keeps a last sentence that ends before an ellipsis', () => {
		expect(reference('They built all of it into JARVIS. … ещё.')?.passage).toBe(
			'They built all of it into JARVIS.'
		);
	});

	test('splits the snippet around the passage', () => {
		const ref = reference(LIST, 'capital of Australia')!;
		expect(ref.before + ref.passage + ref.after).toBe(LIST);
	});

	test('is null when nothing is worth highlighting', () => {
		expect(reference('')).toBeNull();
		expect(reference('Short one.')).toBeNull();
	});
});

describe('highlightUrl', () => {
	test('uses the whole passage when it is short', () => {
		const ref = reference('Canberra is the capital.')!;
		expect(highlightUrl('https://a.com/x', ref)).toBe(
			'https://a.com/x#:~:text=Canberra%20is%20the%20capital.'
		);
	});

	test('uses start and end words for a long passage, escaping - and ,', () => {
		const ref = reference(
			'Dots run on GPT-6 Astra, the flagship model, in every ChatGPT plan today.'
		)!;
		expect(highlightUrl('https://a.com', ref)).toBe(
			'https://a.com#:~:text=Dots%20run%20on%20GPT%2D6,every%20ChatGPT%20plan%20today.'
		);
	});

	test('keeps an existing #fragment', () => {
		const ref = reference('Canberra is the capital.')!;
		expect(highlightUrl('https://a.com/x#top', ref)).toBe(
			'https://a.com/x#top:~:text=Canberra%20is%20the%20capital.'
		);
	});

	test('returns the plain URL without a passage', () => {
		expect(highlightUrl('https://a.com', null)).toBe('https://a.com');
	});
});
