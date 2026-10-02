/**
 * Links that open a source and highlight the passage the model read, using URL text fragments
 * (https://wicg.github.io/scroll-to-text-fragment/): `page#:~:text=start,end`. Browsers without support open the
 * page normally, and a passage the page does not contain is simply not highlighted.
 */

export interface Reference {
	/** The snippet, whitespace collapsed, split around the passage that will be highlighted. */
	before: string;
	passage: string;
	after: string;
}

// a word the page is likely to render exactly as the search engine quoted it
const PLAIN = /^[\p{L}\p{N}'’"“”,.;:!?%$&+/-]+$/u;
const ELLIPSIS = /\s*(?:\.{3}|…)\s*/;
const SENTENCE_END = /[.!?]["”’)]?$/;
// spans that search engines quote differently from the page: (pronunciations), [notes], {templates}
const BRACKETED = /\([^)]*\)|\[[^\]]*]|\{[^}]*}/g;
// one fragment term may hold this many words before start and end are used instead
const WHOLE = 8;
const EDGE = 4;

/** Quotes and apostrophes come straight or curly depending on the page, so an exact match on them is a gamble. */
const QUOTE = /['’"“”]/;

/**
 * Drops words from the ends until the words a fragment matches exactly are free of quotes: all of them when the
 * passage is short enough to be one term, otherwise the first and last few.
 */
function safeEdges(words: string[]): string[] {
	if (words.length <= WHOLE) {
		// the longest quote-free stretch
		let best: string[] = [];
		let run: string[] = [];
		for (const word of [...words, '"']) {
			if (QUOTE.test(word)) {
				if (run.length > best.length) best = run;
				run = [];
			} else run.push(word);
		}
		return best;
	}
	let start = 0;
	let end = words.length;
	while (start < end && words.slice(start, start + EDGE).some((w) => QUOTE.test(w))) start++;
	while (end > start && words.slice(end - EDGE, end).some((w) => QUOTE.test(w))) end--;
	const kept = words.slice(start, end);
	return kept.length > WHOLE ? kept : safeEdges(kept);
}

const STOPWORDS = new Set(
	'the a an and or of to in on at for by with from is are was were be been it its this that what which who whom when where why how does did do as than then into about'.split(
		' '
	)
);

/** The words worth matching: lower case, letters and digits only, no stopwords. */
export function keywords(text: string): Set<string> {
	const words = text.toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
	return new Set(words.filter((w) => w.length > 1 && !STOPWORDS.has(w)));
}

/**
 * The sentence-long run of plain, whole words that shares most words with `about` (the question and the chosen
 * answer), the longer one on a tie; null when none is worth highlighting.
 */
export function reference(content: string, about = ''): Reference | null {
	const text = content.replace(/\s+/g, ' ').trim();
	if (!text) return null;
	const wanted = keywords(about);
	const score = (run: string[]) => [...keywords(run.join(' '))].filter((w) => wanted.has(w)).length;

	let best: string[] = [];
	let bestScore = -1;
	const consider = (run: string[]) => {
		// a run starting or ending on punctuation alone ("-", ",") would not match a word boundary
		while (run.length && !/[\p{L}\p{N}]/u.test(run[0])) run.shift();
		while (run.length && !/[\p{L}\p{N}]/u.test(run.at(-1)!)) run.pop();
		const safe = safeEdges(run);
		if (safe.length < 3) return;
		const s = score(safe);
		if (s > bestScore || (s === bestScore && safe.length > best.length)) {
			best = safe;
			bestScore = s;
		}
	};

	for (const segment of text.split(ELLIPSIS)) {
		// a snippet cut at a character limit, or before an ellipsis, ends in what may be a partial word
		const cut = !SENTENCE_END.test(segment);
		const parts = segment.split(BRACKETED);
		parts.forEach((part, i) => {
			const words = part.trim().split(' ').filter(Boolean);
			if (cut && i === parts.length - 1) words.pop();
			let run: string[] = [];
			for (const word of words) {
				if (!PLAIN.test(word)) {
					consider(run);
					run = [];
					continue;
				}
				run.push(word);
				// one sentence at a time: snippets stitch together text from different parts of a page
				if (SENTENCE_END.test(word)) {
					consider(run);
					run = [];
				}
			}
			consider(run);
		});
	}
	if (best.length < 3) return null;

	const passage = best.join(' ');
	const at = text.indexOf(passage);
	if (at === -1) return null;
	return { before: text.slice(0, at), passage, after: text.slice(at + passage.length) };
}

/** Text fragment syntax gives `-`, `,` and `&` meanings of their own, so they are escaped too. */
function term(text: string) {
	return encodeURIComponent(text).replace(/-/g, '%2D');
}

/** The source URL with a directive that scrolls to and highlights the passage. */
export function highlightUrl(url: string, ref: Reference | null): string {
	if (!ref) return url;
	const words = ref.passage.split(' ');
	const directive =
		words.length <= WHOLE
			? `text=${term(ref.passage)}`
			: `text=${term(words.slice(0, EDGE).join(' '))},${term(words.slice(-EDGE).join(' '))}`;
	// an existing #fragment stays; the directive goes after it
	return `${url}${url.includes('#') ? '' : '#'}:~:${directive}`;
}
