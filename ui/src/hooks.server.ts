import type { Handle } from '@sveltejs/kit/hooks';

const SECURITY_HEADERS = {
	'x-content-type-options': 'nosniff',
	'referrer-policy': 'strict-origin-when-cross-origin',
	'permissions-policy': 'camera=(), microphone=(), geolocation=()',
	'cross-origin-opener-policy': 'same-origin'
};

export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event, {
		// the UI font is on every page; fetching it with the HTML avoids a flash of fallback text
		preload: ({ type }) => type === 'js' || type === 'css' || type === 'font'
	});
	for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
		if (!response.headers.has(name)) response.headers.set(name, value);
	}
	if (event.url.pathname.startsWith('/api/')) response.headers.set('cache-control', 'no-store');
	return response;
};
