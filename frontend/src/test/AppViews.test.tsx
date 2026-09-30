import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { LabProvider } from '../context/LabContext';
import { DashboardPage } from '../pages/DashboardPage';
import { IncidentsPage } from '../pages/IncidentsPage';
import { DevicesPage } from '../pages/DevicesPage';
import { SitesPage } from '../pages/SitesPage';
import { KnowledgePage } from '../pages/KnowledgePage';
import { AuditPage } from '../pages/AuditPage';
import { agentApi } from '../api/agent';
import { portalApi } from '../api/portal';

vi.mock('../api/agent', () => ({
  agentApi: {
    getKnowledgeDocs: vi.fn().mockResolvedValue([
      {
        source: 'troubleshooting.md',
        title: 'Troubleshooting Guide',
        size: 2048,
        lines: 120,
        snippet: 'Standard operational procedures for CCTV',
      },
    ]),
    getKnowledgeDoc: vi.fn().mockResolvedValue({
      source: 'troubleshooting.md',
      title: 'Troubleshooting Guide',
      size: 2048,
      lines: 120,
      content: '# Troubleshooting Guide\nStandard procedures.',
    }),
    searchKnowledge: vi.fn().mockResolvedValue([]),
    getState: vi.fn().mockResolvedValue({ is_running: true, cycle_count: 5 }),
    getHealth: vi.fn().mockResolvedValue({ ok: true, service: 'agent' }),
    getPolicy: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../api/portal', () => ({
  portalApi: {
    getAssets: vi.fn().mockResolvedValue([]),
    getSites: vi.fn().mockResolvedValue([]),
    getActiveFaults: vi.fn().mockResolvedValue([]),
    getActionLog: vi.fn().mockResolvedValue([]),
    getFaultLog: vi.fn().mockResolvedValue([]),
    getFaultHistory: vi.fn().mockResolvedValue([]),
    getSupportedFaults: vi.fn().mockResolvedValue(['rtsp_down', 'network_down']),
  },
}));

describe('Application Page Views Rendering', () => {
  it('renders DashboardPage metrics and headers', () => {
    render(
      <LabProvider>
        <BrowserRouter>
          <DashboardPage />
        </BrowserRouter>
      </LabProvider>
    );

    expect(screen.getByText('Total Monitored')).toBeInTheDocument();
    expect(screen.getAllByText(/Active Incidents/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Technician Required')).toBeInTheDocument();
    expect(screen.getByText('Fleet Health')).toBeInTheDocument();
  });

  it('renders IncidentsPage search and filters', () => {
    render(
      <LabProvider>
        <BrowserRouter>
          <IncidentsPage />
        </BrowserRouter>
      </LabProvider>
    );

    expect(
      screen.getByPlaceholderText(/Search tickets by ID, device, symptom, or root cause.../i)
    ).toBeInTheDocument();
    expect(screen.getByText('Tech Required Only')).toBeInTheDocument();
  });

  it('renders DevicesPage kind filters and search', () => {
    render(
      <LabProvider>
        <BrowserRouter>
          <DevicesPage />
        </BrowserRouter>
      </LabProvider>
    );

    expect(screen.getByPlaceholderText(/Search by device ID, IP, or site.../i)).toBeInTheDocument();
    expect(screen.getByText('All Kinds')).toBeInTheDocument();
    expect(screen.getByText('Cameras')).toBeInTheDocument();
    expect(screen.getByText('NVRs')).toBeInTheDocument();
    expect(screen.getByText('AI Boxes')).toBeInTheDocument();
  });

  it('renders KnowledgePage with search bar', async () => {
    render(
      <BrowserRouter>
        <KnowledgePage />
      </BrowserRouter>
    );

    // Initial render shows skeleton or header once loaded
    expect(
      await screen.findByText(/Operational Knowledge & Troubleshooting Guides/i, {}, { timeout: 3000 })
    ).toBeInTheDocument();
  });

  it('renders AuditPage with tabs', () => {
    render(
      <BrowserRouter>
        <AuditPage />
      </BrowserRouter>
    );

    expect(
      screen.getByText(/Operations Audit Log & Policy Traceability/i)
    ).toBeInTheDocument();
  });
});
