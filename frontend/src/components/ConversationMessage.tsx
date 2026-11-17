import type { WeatherEventResponse } from '../types';
import MessageBubble, { type ChatMessage } from './MessageBubble';
import WeatherEventCard from './WeatherEventCard';

interface ConversationMessageProps {
  message: ChatMessage & { event?: WeatherEventResponse };
  onDecision: (eventId: string, decision: 'approve' | 'reject') => Promise<void>;
}

export default function ConversationMessage({ message, onDecision }: ConversationMessageProps) {
  return (
    <div>
      <MessageBubble message={message} />
      {message.event && (
        <WeatherEventCard event={message.event} onDecision={decision => onDecision(message.event!.event_id, decision)} />
      )}
    </div>
  );
}
