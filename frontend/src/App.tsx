import { useEffect, useRef, useState } from 'react';
import { decideWeatherEvent, getTripContext, sendChatMessage, simulateWeatherChange } from './api';
import Composer from './components/Composer';
import ConversationMessage from './components/ConversationMessage';
import type { ChatMessage } from './components/MessageBubble';
import TripSidebar from './components/TripSidebar';
import WelcomePanel from './components/WelcomePanel';
import type { TripContext, WeatherEventResponse } from './types';

type TranscriptMessage = ChatMessage & { event?: WeatherEventResponse };

const newId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export default function App() {
  const [context, setContext] = useState<TripContext | null>(null);
  const [contextError, setContextError] = useState('');
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const endOfMessages = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getTripContext().then(setContext).catch(error => {
      setContextError(error instanceof Error ? error.message : 'Could not load the demo trip.');
    });
  }, []);

  useEffect(() => {
    if (messages.length > 0 || busy) {
      endOfMessages.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages, busy]);

  const addMessage = (message: TranscriptMessage) => setMessages(current => [...current, message]);

  const ask = async (message: string) => {
    if (busy || !message.trim()) return;
    addMessage({ id: newId(), role: 'user', text: message });
    setBusy(true);
    try {
      const result = await sendChatMessage(message);
      addMessage({ id: newId(), role: 'assistant', text: result.answer, citations: result.citations, itinerary: result.itinerary });
    } catch (error) {
      addMessage({ id: newId(), role: 'assistant', text: `I couldn't reach the concierge service. ${error instanceof Error ? error.message : 'Please try again.'}` });
    } finally {
      setBusy(false);
    }
  };

  const rainSimulation = async () => {
    if (busy) return;
    const outdoorItem = context?.itinerary.find(item => item.setting === 'outdoor' && item.status !== 'cancelled');
    if (!context || !outdoorItem) {
      addMessage({ id: newId(), role: 'assistant', text: contextError || 'I could not find an outdoor activity in the demo itinerary to check.' });
      return;
    }
    const dateLabel = new Date(`${outdoorItem.date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    addMessage({ id: newId(), role: 'user', text: `The forecast changed for ${dateLabel}. Check whether this affects my outdoor plan.` });
    setBusy(true);
    try {
      const event = await simulateWeatherChange(context, outdoorItem);
      addMessage({ id: newId(), role: 'assistant', text: 'Here is the itinerary impact check for the simulated weather change.', citations: [], event });
    } catch (error) {
      addMessage({ id: newId(), role: 'assistant', text: `I couldn't evaluate the weather change. ${error instanceof Error ? error.message : 'Please try again.'}` });
    } finally {
      setBusy(false);
    }
  };

  const decide = async (eventId: string, decision: 'approve' | 'reject') => {
    const updated = await decideWeatherEvent(eventId, decision);
    setMessages(current => current.map(message => message.event?.event_id === eventId ? { ...message, event: updated } : message));
  };

  return (
    <div className="app-shell">
      <TripSidebar context={context} />
      <main className="main-panel">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark">t<span>p</span></span> tripPartner</div>
          <div className="topbar-context"><span className="context-spark">✳</span><span>Here for your Meghalaya journey</span></div>
          <a className="topbar-link" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">API <span>↗</span></a>
        </header>
        {context && (
          <div className="mobile-trip-strip">
            <strong>{context.property.name}</strong>
            <span>{context.property.area} · {new Date(`${context.check_in}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}–{new Date(`${context.check_out}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
          </div>
        )}
        <section className="conversation" aria-label="Trip concierge conversation">
          {messages.length === 0 && <WelcomePanel onPrompt={ask} onRainSimulation={rainSimulation} />}
          {!!contextError && messages.length === 0 && <p className="load-error">Could not load the demo trip: {contextError}</p>}
          <div className="messages" aria-live="polite">
            {messages.map(message => <ConversationMessage key={message.id} message={message} onDecision={decide} />)}
          </div>
          {busy && <div className="typing"><span /><span /><span /><small>tripPartner is thinking</small></div>}
          <div ref={endOfMessages} />
        </section>
        <Composer disabled={busy} onSend={ask} />
      </main>
    </div>
  );
}
