import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatContainer } from '../components/chat/ChatContainer';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { LabProvider } from '../context/LabContext';
import { BrowserRouter } from 'react-router-dom';

describe('AI Assistant Chat & Slash Commands', () => {
  it('renders welcome message and slash command pills', () => {
    render(
      <LabProvider>
        <BrowserRouter>
          <ChatContainer />
        </BrowserRouter>
      </LabProvider>
    );

    expect(screen.getByText(/EG CCTV Operations Autonomous Assistant/i)).toBeInTheDocument();
    expect(screen.getByText('/investigate CAM-001')).toBeInTheDocument();
    expect(screen.getByText('/clear')).toBeInTheDocument();
    expect(screen.getByText('/help')).toBeInTheDocument();
  });

  it('renders system message for /clear command', () => {
    render(
      <BrowserRouter>
        <ChatMessageItem
          message={{
            id: 'clear-1',
            role: 'system',
            content: 'Conversation context cleared.',
            timestamp: new Date().toISOString(),
          }}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('Conversation context cleared.')).toBeInTheDocument();
    expect(
      screen.getByText(/Previous chat context has been removed from this assistant session/i)
    ).toBeInTheDocument();
  });

  it('renders tool activity and technician required banner on message', () => {
    render(
      <BrowserRouter>
        <ChatMessageItem
          message={{
            id: 'msg-1',
            role: 'assistant',
            content: 'RTSP auth failure identified on CAM-002.',
            timestamp: new Date().toISOString(),
            toolCalls: [
              { name: 'check_telemetry', label: 'Checking network and telemetry', status: 'failure' },
              { name: 'search_history', label: 'Historical search', status: 'success' },
            ],
            diagnosis: {
              fault: 'rtsp_auth_failure',
              confidence: 0.99,
              recommendation: 'Verify RTSP credentials',
              safety_class: 'HUMAN_ONLY',
            },
            technicianRequired: true,
            technicianActionText: 'Technician must rotate credentials manually',
          }}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('RTSP auth failure identified on CAM-002.')).toBeInTheDocument();
    expect(screen.getByText('⚠️ Technician Action Required')).toBeInTheDocument();
    expect(screen.getByText('Technician must rotate credentials manually')).toBeInTheDocument();
    expect(screen.getByText('rtsp_auth_failure')).toBeInTheDocument();
    expect(screen.getByText('HUMAN ONLY')).toBeInTheDocument();
  });
});
