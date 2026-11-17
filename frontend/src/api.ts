import type { ChatResponse, TripContext, WeatherEventResponse } from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  const payload: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? (payload as { detail: unknown }).detail
      : null;
    throw new Error(typeof detail === 'string' ? detail : 'The request failed. Please try again.');
  }
  return payload as T;
}

export function getTripContext(): Promise<TripContext> {
  return request<TripContext>('/demo/trip-context');
}

export function sendChatMessage(message: string): Promise<ChatResponse> {
  return request<ChatResponse>('/assistant/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export function simulateWeatherChange(
  context: TripContext,
  itineraryItem: TripContext['itinerary'][number],
): Promise<WeatherEventResponse> {
  return request<WeatherEventResponse>('/events/weather-change', {
    method: 'POST',
    body: JSON.stringify({
      trip_id: context.trip_id,
      forecast_date: itineraryItem.date,
      previous_precipitation_probability: 20,
      current_precipitation_probability: 85,
      area: itineraryItem.area,
      event_source: 'simulated',
    }),
  });
}

export function decideWeatherEvent(
  eventId: string,
  decision: 'approve' | 'reject',
): Promise<WeatherEventResponse> {
  return request<WeatherEventResponse>(`/events/weather-change/${encodeURIComponent(eventId)}/decision`, {
    method: 'POST',
    body: JSON.stringify({ decision }),
  });
}
