const HELPDESK_BASE = import.meta.env.VITE_HELPDESK_URL || '/api/helpdesk';
const PORTAL_BASE = import.meta.env.VITE_PORTAL_URL || '/api/portal';
const AGENT_BASE = import.meta.env.VITE_AGENT_URL || '/api/agent';

export class ApiError extends Error {
  status: number;
  statusText: string;
  data: any;

  constructor(message: string, status: number, statusText: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type') && options?.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errData: any = null;
    try {
      errData = await response.json();
    } catch {
      errData = await response.text();
    }
    const message = (errData && errData.detail) || `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, response.statusText, errData);
  }

  return response.json();
}

export const http = {
  get: <T>(url: string) => request<T>(url, { method: 'GET' }),
  post: <T>(url: string, body?: any) =>
    request<T>(url, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(url: string, body?: any) =>
    request<T>(url, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
};

export { HELPDESK_BASE, PORTAL_BASE, AGENT_BASE };
