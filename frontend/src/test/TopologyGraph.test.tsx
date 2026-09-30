import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TopologyGraph } from '../components/topology/TopologyGraph';
import type { Asset } from '../api/types';

describe('TopologyGraph component', () => {
  const mockAssets: Asset[] = [
    {
      id: 'CAM-001',
      site_id: 'SITE-001',
      name: 'Lobby Camera',
      kind: 'camera',
      ip: '10.10.1.11',
      state: {},
    },
    {
      id: 'NVR-002',
      site_id: 'SITE-001',
      name: 'Lobby NVR',
      kind: 'nvr',
      ip: '10.10.1.10',
      state: {},
    },
  ];

  it('renders gateway, NVR and camera in topology hierarchy', () => {
    render(
      <TopologyGraph
        siteId="SITE-001"
        siteName="Corporate HQ"
        assets={mockAssets}
        activeFaults={{}}
      />
    );

    expect(screen.getByText('Site Gateway')).toBeInTheDocument();
    expect(screen.getAllByText('Lobby NVR').length).toBeGreaterThan(0);
    expect(screen.getByText('Lobby Camera')).toBeInTheDocument();
  });

  it('shows shared dependency warning when NVR is faulty', () => {
    render(
      <TopologyGraph
        siteId="SITE-001"
        siteName="Corporate HQ"
        assets={mockAssets}
        activeFaults={{ 'NVR-002': ['nvr_unavailable'] }}
      />
    );

    expect(
      screen.getByText(/Shared Dependency Warning: Upstream NVR is degraded or unavailable/i)
    ).toBeInTheDocument();
  });
});
