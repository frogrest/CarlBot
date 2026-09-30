import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../components/common/Badge';
import { PolicyBadge } from '../components/common/PolicyBadge';

describe('Badge & PolicyBadge components', () => {
  it('renders healthy status with icon and label', () => {
    render(<Badge status="healthy" label="Online Stream" />);
    expect(screen.getByText('Online Stream')).toBeInTheDocument();
  });

  it('renders technician required status', () => {
    render(<Badge status="pending_technician" />);
    expect(screen.getByText('Tech Required')).toBeInTheDocument();
  });

  it('renders critical status', () => {
    render(<Badge status="critical" label="Connection Refused" />);
    expect(screen.getByText('Connection Refused')).toBeInTheDocument();
  });

  it('renders policy classes correctly', () => {
    const { rerender } = render(<PolicyBadge policyClass="SAFE_REVERSIBLE" />);
    expect(screen.getByText('SAFE / REVERSIBLE')).toBeInTheDocument();

    rerender(<PolicyBadge policyClass="HUMAN_ONLY" />);
    expect(screen.getByText('HUMAN ONLY')).toBeInTheDocument();

    rerender(<PolicyBadge policyClass="APPROVAL_REQUIRED" />);
    expect(screen.getByText('APPROVAL REQUIRED')).toBeInTheDocument();

    rerender(<PolicyBadge policyClass="READ" />);
    expect(screen.getByText('READ')).toBeInTheDocument();
  });
});
