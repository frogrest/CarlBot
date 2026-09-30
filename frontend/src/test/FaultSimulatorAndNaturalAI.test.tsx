import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { LabControlsModal } from '../components/layout/LabControlsModal';
import { ChatContainer } from '../components/chat/ChatContainer';
import { LabProvider } from '../context/LabContext';
import { portalApi } from '../api/portal';
import { agentApi } from '../api/agent';
import { helpdeskApi } from '../api/helpdesk';

// Mock API clients for deterministic TDD testing
vi.mock('../api/portal', () => ({
  portalApi: {
    getAssets: vi.fn(),
    getSites: vi.fn(),
    getSiteHealth: vi.fn(),
    getActiveFaults: vi.fn(),
    getSupportedFaults: vi.fn(),
    injectFault: vi.fn(),
    injectSiteFault: vi.fn(),
    clearFault: vi.fn(),
    clearAllFaults: vi.fn(),
    getActionLog: vi.fn(),
    getFaultHistory: vi.fn(),
  },
  PORTAL_BASE: '/api/portal',
}));

vi.mock('../api/agent', () => ({
  agentApi: {
    getHealth: vi.fn(),
    getState: vi.fn(),
    getPolicy: vi.fn(),
    triggerRun: vi.fn(),
    investigateAsset: vi.fn(),
    getKnowledgeDocs: vi.fn(),
    getKnowledgeDoc: vi.fn(),
    searchKnowledge: vi.fn(),
  },
  AGENT_BASE: '/api/agent',
}));

vi.mock('../api/helpdesk', () => ({
  helpdeskApi: {
    getTickets: vi.fn(),
    getStats: vi.fn(),
    searchTickets: vi.fn(),
  },
  HELPDESK_BASE: '/api/helpdesk',
}));

const mockAssets = [
  {
    id: 'CAM-001',
    site_id: 'SITE-001',
    name: 'Lobby Camera',
    kind: 'camera' as const,
    ip: '10.10.1.11',
    state: { reachable: true, rtsp: 'up', rtsp_auth: true, rtsp_path: true, poe: true },
    effective_state: { reachable: true, rtsp: 'up', rtsp_auth: true, rtsp_path: true, poe: true },
  },
  {
    id: 'CAM-002',
    site_id: 'SITE-002',
    name: 'Parking Camera',
    kind: 'camera' as const,
    ip: '10.10.2.11',
    state: { reachable: true, rtsp: 'up', rtsp_auth: true, rtsp_path: true, poe: true },
    effective_state: { reachable: true, rtsp: 'up', rtsp_auth: true, rtsp_path: true, poe: true },
  },
  {
    id: 'AIBOX-001',
    site_id: 'SITE-001',
    name: 'Detection Box Alpha',
    kind: 'ai_box' as const,
    ip: '10.10.1.20',
    state: { reachable: true, service: 'up', cpu: 35, cloud_sync: 'up' },
    effective_state: { reachable: true, service: 'up', cpu: 35, cloud_sync: 'up' },
  },
  {
    id: 'NVR-001',
    site_id: 'SITE-003',
    name: 'Main NVR',
    kind: 'nvr' as const,
    ip: '10.10.3.10',
    state: { reachable: true, storage_used: 55 },
    effective_state: { reachable: true, storage_used: 55 },
  },
];

const mockSupportedFaults = [
  'rtsp_down',
  'rtsp_auth_failure',
  'poe_power_off',
  'high_cpu',
  'storage_full',
  'ai_box_service_failure',
];

describe('Fault Simulator and Natural AI QA Audit Suite', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();

    vi.mocked(portalApi.getAssets).mockResolvedValue(mockAssets);
    vi.mocked(portalApi.getSites).mockResolvedValue([
      { id: 'SITE-001', name: 'Corporate Lobby', location: 'Building A', assets: [] },
      { id: 'SITE-002', name: 'Parking & Loading', location: 'Building B', assets: [] },
      { id: 'SITE-003', name: 'Data Center', location: 'Building C', assets: [] },
    ]);
    vi.mocked(portalApi.getActiveFaults).mockResolvedValue({});
    // Backend returns raw string array
    vi.mocked(portalApi.getSupportedFaults).mockResolvedValue(mockSupportedFaults);
    vi.mocked(portalApi.injectFault).mockResolvedValue({ asset_id: 'CAM-001', active_faults: ['rtsp_down'] });
    vi.mocked(portalApi.clearAllFaults).mockResolvedValue({ cleared: 0, message: 'All cleared' });

    vi.mocked(agentApi.getHealth).mockResolvedValue({ ok: true, service: 'agent' });
    vi.mocked(agentApi.getState).mockResolvedValue({ is_running: true, cycle_count: 10 } as any);
    vi.mocked(agentApi.searchKnowledge).mockResolvedValue([
      {
        source: 'troubleshooting.md',
        score: 1.0,
        snippet: 'RTSP auth failure requires technician credential verification in camera web UI.',
      },
    ]);
    vi.mocked(agentApi.getPolicy).mockResolvedValue({});

    vi.mocked(helpdeskApi.getTickets).mockResolvedValue([]);
  });

  describe('Fault Simulator QA', () => {
    it('renders fault dropdown with supported faults without throwing TypeError', async () => {
      render(
        <LabProvider>
          <LabControlsModal isOpen={true} onClose={() => {}} />
        </LabProvider>
      );

      await waitFor(() => {
        expect(screen.getByText(/CCTV Operations Fault Simulator/i)).toBeInTheDocument();
      });

      // Verify fault options are present
      expect(screen.getByRole('option', { name: 'rtsp_down' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'rtsp_auth_failure' })).toBeInTheDocument();
    });

    it('triggers injectFault on quick scenario click', async () => {
      render(
        <LabProvider>
          <LabControlsModal isOpen={true} onClose={() => {}} />
        </LabProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('1. Safe RTSP Down')).toBeInTheDocument();
      });

      const btn = screen.getByText('1. Safe RTSP Down').closest('button');
      expect(btn).not.toBeNull();
      fireEvent.click(btn!);

      expect(portalApi.injectFault).toHaveBeenCalledWith('CAM-001', 'rtsp_down');
    });

    it('triggers injectFault for hardware fault on CAM-002', async () => {
      render(
        <LabProvider>
          <LabControlsModal isOpen={true} onClose={() => {}} />
        </LabProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('2. RTSP Auth Failure')).toBeInTheDocument();
      });

      const btn = screen.getByText('2. RTSP Auth Failure').closest('button');
      fireEvent.click(btn!);

      expect(portalApi.injectFault).toHaveBeenCalledWith('CAM-002', 'rtsp_auth_failure');
    });
  });

  describe('Natural Language AI Assistant Workflow', () => {
    it('answers natural question about a healthy device without claiming technician escalation', async () => {
      vi.mocked(agentApi.investigateAsset).mockResolvedValue({
        asset_id: 'CAM-001',
        is_problem: false,
        check: { ping: true, rtsp: true, poe: true, rtsp_auth: true, rtsp_path: true },
        asset: mockAssets[0],
        diagnosis: { fault: 'none', confidence: 1.0, recommendation: 'None', safety_class: 'READ' as any },
        policy: { action: 'none', safety_class: 'READ' as any, allowed_automatically: true },
        action_executed: null,
        ticket: null,
        historical_matches: [],
        knowledge_sources: [],
        timeline: [],
        site_info: null,
      });

      render(
        <LabProvider>
          <BrowserRouter>
            <ChatContainer />
          </BrowserRouter>
        </LabProvider>
      );

      const input = screen.getByPlaceholderText(/Ask the AI or type a slash command/i);
      fireEvent.change(input, { target: { value: 'How is CAM-001 doing?' } });

      const sendBtn = screen.getByRole('button', { name: /Send/i });
      fireEvent.click(sendBtn);

      await waitFor(() => {
        expect(screen.getByText(/All subsystem telemetry is normal/i)).toBeInTheDocument();
      });

      // Crucial: Must NOT state technician escalation for a healthy device!
      expect(screen.queryByText(/Escalated to human technician/i)).toBeNull();
      expect(screen.queryByText(/⚠️ Technician Action Required/i)).toBeNull();
    });

    it('handles natural question asking for active faults and system overview', async () => {
      render(
        <LabProvider>
          <BrowserRouter>
            <ChatContainer />
          </BrowserRouter>
        </LabProvider>
      );

      const input = screen.getByPlaceholderText(/Ask the AI or type a slash command/i);
      fireEvent.change(input, { target: { value: 'What faults are currently active across the system?' } });
      fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

      await waitFor(() => {
        expect(screen.getByText(/Fleet Operational Status/i)).toBeInTheDocument();
      });
    });

    it('handles natural question about camera aliases like "lobby camera"', async () => {
      vi.mocked(agentApi.investigateAsset).mockResolvedValue({
        asset_id: 'CAM-001',
        is_problem: false,
        check: { ping: true, rtsp: true, poe: true },
        asset: mockAssets[0],
        diagnosis: { fault: 'none', confidence: 1.0, recommendation: 'None', safety_class: 'READ' as any },
        policy: { action: 'none', safety_class: 'READ' as any, allowed_automatically: true },
        action_executed: null,
        ticket: null,
        historical_matches: [],
        knowledge_sources: [],
        timeline: [],
        site_info: null,
      });

      render(
        <LabProvider>
          <BrowserRouter>
            <ChatContainer />
          </BrowserRouter>
        </LabProvider>
      );

      const input = screen.getByPlaceholderText(/Ask the AI or type a slash command/i);
      fireEvent.change(input, { target: { value: 'Check the lobby camera please' } });

      const sendBtn = screen.getByRole('button', { name: /Send/i });
      fireEvent.click(sendBtn);

      await waitFor(() => {
        expect(agentApi.investigateAsset).toHaveBeenCalledWith('CAM-001');
      });
    });

    it('explains safety policy when asked in natural language', async () => {
      render(
        <LabProvider>
          <BrowserRouter>
            <ChatContainer />
          </BrowserRouter>
        </LabProvider>
      );

      const input = screen.getByPlaceholderText(/Ask the AI or type a slash command/i);
      fireEvent.change(input, { target: { value: 'Can you explain the safety policy tiers?' } });

      const sendBtn = screen.getByRole('button', { name: /Send/i });
      fireEvent.click(sendBtn);

      await waitFor(() => {
        expect(screen.getByText(/SAFE_REVERSIBLE/i)).toBeInTheDocument();
        expect(screen.getByText(/HUMAN_ONLY/i)).toBeInTheDocument();
      });
    });
  });
});
