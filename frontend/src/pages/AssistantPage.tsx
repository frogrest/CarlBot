import React from 'react';
import { ChatContainer } from '../components/chat/ChatContainer';

export const AssistantPage: React.FC = () => {
  return (
    <div className="h-full w-full overflow-hidden">
      <ChatContainer />
    </div>
  );
};
