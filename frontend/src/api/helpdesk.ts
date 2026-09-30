import { http, HELPDESK_BASE } from './client';
import type { Ticket } from './types';

export const helpdeskApi = {
  async getTickets(params?: { status?: string; site_id?: string; asset_id?: string }): Promise<Ticket[]> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.site_id) query.set('site_id', params.site_id);
    if (params?.asset_id) query.set('asset_id', params.asset_id);
    const qs = query.toString();
    return http.get<Ticket[]>(`${HELPDESK_BASE}/tickets${qs ? `?${qs}` : ''}`);
  },

  async getTicket(id: string): Promise<Ticket> {
    return http.get<Ticket>(`${HELPDESK_BASE}/tickets/${id}`);
  },

  async createTicket(data: {
    title: string;
    description: string;
    site_id: string;
    asset_id?: string;
    tags?: string[];
  }): Promise<Ticket> {
    return http.post<Ticket>(`${HELPDESK_BASE}/tickets`, data);
  },

  async updateTicket(id: string, data: Partial<Ticket>): Promise<Ticket> {
    return http.patch<Ticket>(`${HELPDESK_BASE}/tickets/${id}`, data);
  },

  async addComment(id: string, author: string, body: string): Promise<Ticket> {
    return http.post<Ticket>(`${HELPDESK_BASE}/tickets/${id}/comments`, { author, body });
  },

  async addTechnicianNote(id: string, author: string, body: string): Promise<Ticket> {
    return http.post<Ticket>(`${HELPDESK_BASE}/tickets/${id}/technician-notes`, { author, body });
  },

  async search(query: string): Promise<Ticket[]> {
    return http.get<Ticket[]>(`${HELPDESK_BASE}/search?q=${encodeURIComponent(query)}`);
  },

  async getStats(): Promise<{
    total: number;
    open: number;
    investigating: number;
    pending_technician: number;
    pending_approval: number;
    resolved: number;
  }> {
    return http.get(`${HELPDESK_BASE}/stats`);
  },
};
