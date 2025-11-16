import { kindeAuthClient } from '@kinde-oss/kinde-auth-sveltekit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import { redirect } from '@sveltejs/kit';

const resolveLogoutRedirect = () => {
	return (
		env.KINDE_POST_LOGOUT_REDIRECT_URL ||
		env.KINDE_POST_LOGIN_REDIRECT_URL ||
		env.KINDE_REDIRECT_URL
	);
};

export const GET: RequestHandler = async (event) => {
	const redirectTarget = resolveLogoutRedirect() || '/';

	const url = await kindeAuthClient.logout(
		event.request as Parameters<typeof kindeAuthClient.logout>[0]
	);

	url.searchParams.set('post_logout_redirect_uri', redirectTarget);
	url.searchParams.set('logout_redirect_url', redirectTarget);

	throw redirect(302, url.toString());
};
