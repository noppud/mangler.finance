import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';

const BACKEND_URL = env.BACKEND_URL || 'https://fintech-hackathon-production.up.railway.app';

// Helper to handle special routes
function handlePath(path: string | undefined): string {
  // Special handling for "current" endpoint that doesn't exist in backend
  if (path === 'current') {
    return 'link'; // Map to link endpoint and handle 404 gracefully
  }
  return path || '';
}

export const GET: RequestHandler = async ({ request, params, locals }) => {
  const session = await locals.getKindeSession();
  if (!session?.user) {
    return new Response('Unauthorized', { status: 401 });
  }

  const path = handlePath(params.path);
  const url = `${BACKEND_URL}/identity/${path}`;

  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${session.accessToken}`,
      },
    });

    // Special handling for "current" - return 404 if no link exists
    if (params.path === 'current' && response.status === 404) {
      return new Response(null, { status: 404 });
    }

    const data = await response.text();
    return new Response(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Identity API proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
};

export const POST: RequestHandler = async ({ request, params, locals }) => {
  const path = params.path || '';
  const url = `${BACKEND_URL}/identity/${path}`;
  const body = await request.text();

  // For resolve endpoint, no auth required (public)
  if (path === 'resolve') {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body,
      });

      const data = await response.text();
      return new Response(data, {
        status: response.status,
        headers: {
          'Content-Type': response.headers.get('Content-Type') || 'application/json',
        },
      });
    } catch (error) {
      console.error('Identity API proxy error:', error);
      return new Response('Internal Server Error', { status: 500 });
    }
  }

  // For other endpoints, require auth
  const session = await locals.getKindeSession();
  if (!session?.user) {
    return new Response('Unauthorized', { status: 401 });
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session.accessToken}`,
        'Content-Type': 'application/json',
      },
      body,
    });

    const data = await response.text();
    return new Response(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Identity API proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
};

export const DELETE: RequestHandler = async ({ request, params, locals }) => {
  const session = await locals.getKindeSession();
  if (!session?.user) {
    return new Response('Unauthorized', { status: 401 });
  }

  const path = params.path || '';
  const url = `${BACKEND_URL}/identity/${path}`;

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${session.accessToken}`,
      },
    });

    const data = await response.text();
    return new Response(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Identity API proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
};