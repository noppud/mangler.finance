import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import { kindeAuthClient, type SessionManager } from '@kinde-oss/kinde-auth-sveltekit';

const BACKEND_URL = env.BACKEND_URL || 'https://fintech-hackathon-production.up.railway.app';

export const GET: RequestHandler = async ({ request, params }) => {
  const sessionManager = request as unknown as SessionManager;
  const isAuthenticated = await kindeAuthClient.isAuthenticated(sessionManager);

  if (!isAuthenticated) {
    return new Response('Unauthorized', { status: 401 });
  }

  const token = await kindeAuthClient.getToken(sessionManager);
  const path = params.path;
  const url = `${BACKEND_URL}/mcp/${path}`;

  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
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
    console.error('MCP API proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
};

export const POST: RequestHandler = async ({ request, params }) => {
  const sessionManager = request as unknown as SessionManager;
  const isAuthenticated = await kindeAuthClient.isAuthenticated(sessionManager);

  if (!isAuthenticated) {
    return new Response('Unauthorized', { status: 401 });
  }

  const token = await kindeAuthClient.getToken(sessionManager);
  const path = params.path;
  const url = `${BACKEND_URL}/mcp/${path}`;
  const body = await request.text();

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
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
    console.error('MCP API proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
};

export const PATCH: RequestHandler = async ({ request, params }) => {
  const sessionManager = request as unknown as SessionManager;
  const isAuthenticated = await kindeAuthClient.isAuthenticated(sessionManager);

  if (!isAuthenticated) {
    return new Response('Unauthorized', { status: 401 });
  }

  const token = await kindeAuthClient.getToken(sessionManager);
  const path = params.path;
  const url = `${BACKEND_URL}/mcp/${path}`;
  const body = await request.text();

  try {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
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
    console.error('MCP API proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
};

export const DELETE: RequestHandler = async ({ request, params }) => {
  const sessionManager = request as unknown as SessionManager;
  const isAuthenticated = await kindeAuthClient.isAuthenticated(sessionManager);

  if (!isAuthenticated) {
    return new Response('Unauthorized', { status: 401 });
  }

  const token = await kindeAuthClient.getToken(sessionManager);
  const path = params.path;
  const url = `${BACKEND_URL}/mcp/${path}`;

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
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
    console.error('MCP API proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
};