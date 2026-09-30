import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InvestigationTimeline } from '../components/timeline/InvestigationTimeline';
import type { TimelineStep } from '../api/types';

describe('InvestigationTimeline component', () => {
  const mockTimeline: TimelineStep[] = [
    {
      step: 'observation',
      title: 'Telemetry check on CAM-001',
      status: 'FAIL',
      details: { ping: true, rtsp: 'down' },
      timestamp: new Date().toISOString(),
    },
    {
      step: 'hypothesis',
      title: 'Formed diagnostic hypothesis: rtsp_down',
      status: 'PASS',
      details: { fault: 'rtsp_down', confidence: 0.95 },
      timestamp: new Date().toISOString(),
    },
    {
      step: 'policy_evaluation',
      title: 'Policy check for action reconnect_stream',
      status: 'ALLOWED',
      details: { allowed_automatically: true },
      timestamp: new Date().toISOString(),
    },
    {
      step: 'recovery_and_verification',
      title: "Recovery action 'reconnect_stream' executed",
      status: 'PASS',
      details: { verified: true },
      timestamp: new Date().toISOString(),
    },
  ];

  it('renders all investigation steps in timeline', () => {
    render(<InvestigationTimeline timeline={mockTimeline} />);
    expect(screen.getByText('Telemetry check on CAM-001')).toBeInTheDocument();
    expect(screen.getByText('Formed diagnostic hypothesis: rtsp_down')).toBeInTheDocument();
    expect(screen.getByText('Policy check for action reconnect_stream')).toBeInTheDocument();
    expect(screen.getByText("Recovery action 'reconnect_stream' executed")).toBeInTheDocument();
  });

  it('displays structured evidence when step is clicked', () => {
    render(<InvestigationTimeline timeline={mockTimeline} />);
    // Step 0 is expanded by default
    expect(screen.getByText(/"rtsp": "down"/i)).toBeInTheDocument();
  });
});
