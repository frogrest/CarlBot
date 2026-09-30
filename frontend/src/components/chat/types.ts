import type { SafetyClass, TimelineStep } from '../../api/types';

export interface ChatToolCall {
  name: string;
  label: string;
  status: 'running' | 'success' | 'failure' | 'blocked' | 'skipped';
  result?: any;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  toolCalls?: ChatToolCall[];
  diagnosis?: {
    fault: string;
    confidence: number;
    recommendation: string;
    safety_class: SafetyClass;
  };
  policy?: {
    action: string | null;
    safety_class: SafetyClass;
    allowed_automatically: boolean;
  };
  actionExecuted?: string | null;
  technicianRequired?: boolean;
  technicianActionText?: string;
  timeline?: TimelineStep[];
  citations?: Array<{ source: string; score: number; snippet: string }>;
  ticketId?: string;
}

export interface ChatConversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}
