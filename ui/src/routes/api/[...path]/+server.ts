import { WEB_SEARCH_URL } from '$app/env/private';
import type { RequestHandler } from './$types';

const FORWARDED = ['content-type', 'authorization', 'x-web-search', 'x-typesafe-request-id'];
const PATHS = /^(health|v1\/systemone)$/;
// Kev may search twice and answer three times; give it room, but never hang forever
const TIMEOUT_MS = 180_000;

/** Forwards the routes the app uses to the FastAPI server, so the browser never needs CORS. */
const forward: RequestHandler = async ({ request, params, url, fetch }) => {
	if (!PATHS.test(params.path)) return Response.json({ detail: 'Not found' }, { status: 404 });

	const headers = new Headers();
	for (const name of FORWARDED) {
		const value = request.headers.get(name);
		if (value) headers.set(name, value);
	}
	const body = request.method === 'GET' ? undefined : await request.text();
	// the browser aborting (Stop) aborts the upstream request too
	const signal = AbortSignal.any([request.signal, AbortSignal.timeout(TIMEOUT_MS)]);

	try {
		const upstream = await fetch(`${WEB_SEARCH_URL}/${params.path}${url.search}`, {
			method: request.method,
			headers,
			body,
			signal
		});
		return new Response(upstream.body, {
			status: upstream.status,
			headers: {
				'content-type': upstream.headers.get('content-type') ?? 'application/json',
				'x-typesafe-request-id': upstream.headers.get('x-typesafe-request-id') ?? ''
			}
		});
	} catch (e) {
		const timedOut = e instanceof DOMException && e.name === 'TimeoutError';
		return Response.json(
			{
				detail: timedOut
					? 'The server took too long to answer'
					: `Server unreachable at ${WEB_SEARCH_URL}`
			},
			{ status: timedOut ? 504 : 502 }
		);
	}
};

export const GET = forward;
export const POST = forward;
