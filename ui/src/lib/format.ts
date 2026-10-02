export const percent = (x: number) => `${Math.round(x * 100)}%`;

export function seconds(ms: number | undefined) {
	if (ms === undefined) return '';
	return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function domain(url: string) {
	try {
		return new URL(url).hostname.replace(/^www\./, '');
	} catch {
		return url;
	}
}

/** "before_2024" → "Before 2024" when the criteria give no nicer name. */
export function humanize(id: string) {
	const words = id.replace(/[_-]+/g, ' ').trim();
	return words.charAt(0).toUpperCase() + words.slice(1);
}

export type Tier = 'high' | 'mid' | 'low';

/** Low is below the search threshold (Kev was unsure); high is a clear answer. */
export function tier(confidence: number, threshold = 0.5): Tier {
	if (confidence < threshold) return 'low';
	return confidence >= 0.8 ? 'high' : 'mid';
}

export const TIER_LABEL: Record<Tier, string> = { high: 'High', mid: 'Medium', low: 'Low' };
