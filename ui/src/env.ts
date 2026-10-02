import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	WEB_SEARCH_URL: {
		description: 'The web-search proxy that /api forwards to',
		schema: (value) => (value || 'http://127.0.0.1:8009').replace(/\/$/, '')
	}
});
