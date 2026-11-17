import type { Citation } from '../types';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
  itinerary?: Array<{
    date: string;
    place_id: string;
    title: string;
    area: string;
    start_time: string | null;
    end_time: string | null;
  }>;
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const itineraryByDate = (message.itinerary ?? []).reduce<Record<string, NonNullable<ChatMessage['itinerary']>>>(
    (groups, item) => {
      groups[item.date] = [...(groups[item.date] ?? []), item];
      return groups;
    },
    {},
  );

  return (
    <article className={`message ${message.role}`}>
      <div className="message-label">
        {message.role === 'assistant' ? <><span className="mini-mark">✳</span>tripPartner</> : 'YOU'}
      </div>
      <div className="bubble">{message.text}</div>
      {!!message.itinerary?.length && (
        <section className="itinerary-card" aria-label="Validated suggested itinerary">
          {Object.entries(itineraryByDate).map(([day, items], index) => (
            <div className="itinerary-day" key={day}>
              <h3>Day {index + 1} · {new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</h3>
              <ul>{items?.map(item => (
                <li key={`${day}-${item.place_id}`}>
                  <span className="itinerary-time">{item.start_time && item.end_time ? `${item.start_time.slice(0, 5)}–${item.end_time.slice(0, 5)}` : 'Flexible'}</span>
                  <span><strong>{item.title}</strong><small>{item.area}</small></span>
                </li>
              ))}</ul>
            </div>
          ))}
        </section>
      )}
      {!!message.citations?.length && (
        <div className="citation-list">
          {message.citations.map((citation, index) => (
            <a className="citation" href={citation.url} target="_blank" rel="noreferrer" key={`${citation.source_id}-${index}`}>
              {citation.title}<span>↗</span>
            </a>
          ))}
        </div>
      )}
    </article>
  );
}
