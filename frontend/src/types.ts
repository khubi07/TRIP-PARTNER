export interface TripContext {
  trip_id: string;
  booking_reference: string;
  check_in: string;
  check_out: string;
  guest_count: number;
  property: {
    name: string;
    area: string;
  };
  preferences: {
    interests: string[];
    preferred_vibe: string[];
    dietary_preferences: string[];
  };
  itinerary: Array<{
    item_id: string;
    date: string;
    title: string;
    place_id: string | null;
    area: string;
    category: string;
    setting: 'indoor' | 'outdoor' | 'mixed';
    status: 'planned' | 'approved' | 'cancelled';
  }>;
}

export interface Citation {
  source_id: string;
  source_type: string;
  title: string;
  url: string;
}

export interface ChatResponse {
  intent: string;
  answer: string;
  citations: Citation[];
  itinerary: Array<{
    date: string;
    place_id: string;
    title: string;
    area: string;
    start_time: string | null;
    end_time: string | null;
  }>;
  needs_refinement: boolean;
  fallback_message: string | null;
}

export interface WeatherEventResponse {
  event_id: string;
  trip_id: string;
  forecast_date: string;
  event_source: 'simulated' | 'open_meteo';
  status: 'no_action' | 'no_alternative_found' | 'suggestion_created';
  precipitation_change: number;
  affected_item_ids: string[];
  message: string;
  suggested_alternative: {
    place_id: string;
    title: string;
    area: string;
    summary: string;
    setting: 'indoor' | 'outdoor' | 'mixed';
  } | null;
  citations: Citation[];
  requires_guest_approval: boolean;
  llm_used: boolean;
  approval_status: 'pending' | 'approved' | 'rejected' | null;
}
