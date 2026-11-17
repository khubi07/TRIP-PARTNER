import { useState } from 'react';
import type { WeatherEventResponse } from '../types';

interface WeatherEventCardProps {
  event: WeatherEventResponse;
  onDecision: (decision: 'approve' | 'reject') => Promise<void>;
}

export default function WeatherEventCard({ event, onDecision }: WeatherEventCardProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const decide = async (decision: 'approve' | 'reject') => {
    setSaving(true);
    setError('');
    try {
      await onDecision(decision);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not save your decision.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="event-card">
      <h3>{event.suggested_alternative ? `A weather-aware alternative: ${event.suggested_alternative.title}` : 'Weather check complete'}</h3>
      <p>{event.message}</p>
      {event.suggested_alternative && <p className="event-summary">{event.suggested_alternative.area} · {event.suggested_alternative.summary}</p>}
      {!!event.citations.length && (
        <div className="citation-list">
          {event.citations.map((source, index) => <a className="citation" href={source.url} target="_blank" rel="noreferrer" key={`${source.source_id}-${index}`}>{source.title}<span>↗</span></a>)}
        </div>
      )}
      {event.requires_guest_approval && event.approval_status === 'pending' ? (
        <div className="event-actions">
          <button className="approve" onClick={() => decide('approve')} disabled={saving}>Approve change</button>
          <button onClick={() => decide('reject')} disabled={saving}>Keep my plan</button>
        </div>
      ) : (
        <span className="event-status">
          {event.approval_status === 'approved' ? 'Plan updated' : event.approval_status === 'rejected' ? 'Original plan kept' : event.status.replaceAll('_', ' ')}
        </span>
      )}
      {event.approval_status === 'approved' && <p className="event-summary">Your approved alternative is now in the trip itinerary.</p>}
      {error && <p className="error-note">{error}</p>}
    </section>
  );
}
