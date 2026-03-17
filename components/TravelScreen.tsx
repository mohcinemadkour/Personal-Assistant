import React, { useState, useEffect } from 'react';
import { CalendarEvent } from '../types';
import { Button } from './Button';

interface TravelEvent extends CalendarEvent {
  duration: number; // in days
  isTravelEvent: boolean;
  distance?: number; // in miles
}

interface Hotel {
  name: string;
  address?: string;
  city: string;
  country: string;
  price_per_night: number;
  rating: number;
  bedrooms: number;
  url: string;
  map_url: string;
}

interface HotelFilters {
  bedrooms: number;
  maxPrice: number;
  minRating: number;
  adults: number;
  children: number;
  sortBy: string;
  currency: string;
}

const DEFAULT_HOTEL_FILTERS: HotelFilters = {
  bedrooms: 1,
  maxPrice: 300,
  minRating: 3.5,
  adults: 2,
  children: 0,
  sortBy: 'rating',
  currency: 'USD',
};

interface HotelSuggestions {
  eventId: string;
  hotels: Hotel[];
  loading: boolean;
  error?: string;
}

// Approximate coordinates for major US cities (latitude, longitude)
const CITY_COORDINATES: Record<string, { lat: number; lon: number }> = {
  'dallas': { lat: 32.7767, lon: -96.7970 },
  'houston': { lat: 29.7604, lon: -95.3698 },
  'austin': { lat: 30.2672, lon: -97.7431 },
  'san antonio': { lat: 29.4241, lon: -98.4936 },
  'fort worth': { lat: 32.7555, lon: -97.3308 },
  'frisco': { lat: 33.1614, lon: -96.8236 },
  'plano': { lat: 33.0198, lon: -96.6989 },
  'richardson': { lat: 32.9483, lon: -96.7313 },
  'arlington': { lat: 32.7357, lon: -97.1081 },
  'irving': { lat: 32.8153, lon: -97.2244 },
  'atlanta': { lat: 33.7490, lon: -84.3880 },
  'chicago': { lat: 41.8781, lon: -87.6298 },
  'new york': { lat: 40.7128, lon: -74.0060 },
  'los angeles': { lat: 34.0522, lon: -118.2437 },
  'san francisco': { lat: 37.7749, lon: -122.4194 },
  'denver': { lat: 39.7392, lon: -104.9903 },
  'boston': { lat: 42.3601, lon: -71.0589 },
  'washington': { lat: 38.9072, lon: -77.0369 },
  'london': { lat: 51.5074, lon: -0.1278 },
  'toronto': { lat: 43.6532, lon: -79.3832 },
  'mexico city': { lat: 19.4326, lon: -99.1332 },
};

// Haversine formula to calculate distance between two coordinates
function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 3959; // Earth's radius in miles
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Extract city from location string
function extractCity(location: string): string | null {
  if (!location) return null;
  
  const locationLower = location.toLowerCase();
  
  // Try to match against known cities in CITY_COORDINATES
  for (const city of Object.keys(CITY_COORDINATES)) {
    if (locationLower.includes(city)) {
      return city;
    }
  }
  
  // Fallback: try to extract city from format like "City Name, State" or "City Name"
  const parts = locationLower.split(/[,\-]/);
  if (parts.length > 0) {
    const candidate = parts[0].trim();
    // Check if the first part is a known city
    if (CITY_COORDINATES[candidate]) {
      return candidate;
    }
  }
  
  return null;
}

export const TravelScreen: React.FC = () => {
  const [travelEvents, setTravelEvents] = useState<TravelEvent[]>([]);
  const [allEvents, setAllEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [homeLocation, setHomeLocation] = useState<string | null>(null);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [hotelSuggestions, setHotelSuggestions] = useState<Map<string, HotelSuggestions>>(new Map());
  const [hotelFilters, setHotelFilters] = useState<Map<string, HotelFilters>>(new Map());

  useEffect(() => {
    // Retrieve home location and booking platform from localStorage (preferences)
    try {
      const prefsStr = localStorage.getItem('preferences');
      if (prefsStr) {
        const prefs = JSON.parse(prefsStr);
        if (prefs.homeLocation) {
          setHomeLocation(prefs.homeLocation);
        }
      }
    } catch (e) {
      console.error('Failed to load preferences:', e);
    }
  }, []);

  // Fetch events after home location is set
  useEffect(() => {
    if (homeLocation) {
      fetchTravelEvents();
    }
  }, [homeLocation]);

  const fetchTravelEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/calendar/events?days=365');
      const data = await response.json();
      
      if (!response.ok) {
        const errorMsg = data.error || response.statusText;
        if (response.status === 401) {
          throw new Error(
            `Google credentials not configured. Please upload your Google credentials in Settings to access your calendar.`
          );
        }
        throw new Error(`Failed to fetch calendar events: ${errorMsg}`);
      }
      
      const events = data.events || [];
      setAllEvents(events);
      
      // Filter for travel-related events
      const filtered = filterTravelEvents(events, homeLocation);
      setTravelEvents(filtered);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch travel events');
      console.error('Travel fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const filterTravelEvents = (events: CalendarEvent[], home: string | null): TravelEvent[] => {
    return events
      .filter((event) => {
        // Must have a location and not be an online/virtual meeting
        if (!event.location || event.location.trim() === '') {
          return false;
        }
        
        const locationLower = event.location.toLowerCase();
        if (locationLower.includes('online') || locationLower.includes('virtual') || locationLower.includes('zoom') || locationLower.includes('teams')) {
          return false;
        }
        
        // If we have a home location, calculate distance and enforce 100+ mile requirement
        if (home) {
          const homeCity = extractCity(home);
          const eventCity = extractCity(event.location);
          
          if (homeCity && eventCity) {
            const homeCoords = CITY_COORDINATES[homeCity];
            const eventCoords = CITY_COORDINATES[eventCity];
            
            // If we have coordinates for both cities, calculate distance
            if (homeCoords && eventCoords) {
              const distance = calculateDistance(homeCoords.lat, homeCoords.lon, eventCoords.lat, eventCoords.lon);
              // Only show events 100+ miles away
              if (distance < 100) {
                return false;
              }
              return true;
            } else {
              // Location cannot be resolved to known coordinates - filter it out
              return false;
            }
          } else {
            // Could not extract cities - filter it out
            return false;
          }
        }
        
        return true;
      })
      .map((event) => {
        const start = new Date(event.startTime);
        const end = new Date(event.endTime);
        const duration = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
        
        // Calculate distance if home location is set
        let distance: number | undefined;
        if (home) {
          const homeCity = extractCity(home);
          const eventCity = extractCity(event.location);
          if (homeCity && eventCity) {
            const homeCoords = CITY_COORDINATES[homeCity];
            const eventCoords = CITY_COORDINATES[eventCity];
            if (homeCoords && eventCoords) {
              distance = Math.round(calculateDistance(homeCoords.lat, homeCoords.lon, eventCoords.lat, eventCoords.lon));
            }
          }
        }
        
        return {
          ...event,
          duration: Math.max(1, duration),
          isTravelEvent: !!event.location,
          distance
        };
      })
      .sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime());
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getTravelType = (event: TravelEvent): string => {
    const title = event.title.toLowerCase();
    const location = event.location?.toLowerCase() || '';
    
    if (title.includes('flight') || title.includes('flight booking')) return 'Flight';
    if (title.includes('hotel')) return 'Accommodation';
    if (title.includes('conference') || title.includes('summit')) return 'Conference';
    if (title.includes('road trip') || title.includes('drive')) return 'Road Trip';
    if (title.includes('vacation') || title.includes('leave')) return 'Vacation';
    if (event.location) return 'Business Travel';
    return 'Trip';
  };

  const getFiltersForEvent = (eventId: string): HotelFilters =>
    hotelFilters.get(eventId) || { ...DEFAULT_HOTEL_FILTERS };

  const updateFilterForEvent = (eventId: string, key: keyof HotelFilters, value: number | string) => {
    setHotelFilters(prev => {
      const current = prev.get(eventId) || { ...DEFAULT_HOTEL_FILTERS };
      return new Map(prev).set(eventId, { ...current, [key]: value });
    });
    // Clear cached results so new search uses updated filters
    setHotelSuggestions(prev => { const next = new Map(prev); next.delete(eventId); return next; });
  };

  const fetchHotelSuggestions = async (event: TravelEvent, forceRefetch = false) => {
    const eventId = event.id;
    
    console.log('[Travel] Fetching hotels for event:', event);
    
    // If already fetched and not forced, don't fetch again
    if (!forceRefetch && hotelSuggestions.has(eventId)) {
      console.log('[Travel] Hotels already fetched for this event, skipping');
      return;
    }
    
    // Set loading state
    setHotelSuggestions(prev => new Map(prev).set(eventId, {
      eventId,
      hotels: [],
      loading: true,
    }));
    
    try {
      // Extract city from location
      const eventCity = extractCity(event.location);
      console.log('[Travel] Extracted city:', eventCity, 'from location:', event.location);
      
      if (!eventCity) {
        throw new Error('Could not extract city from location');
      }
      
      // Format dates for API
      const startDate = event.startTime.split('T')[0];
      const endDate = event.endTime.split('T')[0];
      
      const filters = hotelFilters.get(eventId) || DEFAULT_HOTEL_FILTERS;
      console.log('[Travel] Fetching hotels for:', { eventCity, startDate, endDate, filters });
      
      // Get hotel suggestions with all filter params
      const url = `/api/hotel-suggestions?destination=${encodeURIComponent(eventCity)}&start_date=${startDate}&end_date=${endDate}&bedrooms=${filters.bedrooms}&max_price=${filters.maxPrice}&min_rating=${filters.minRating}&adults=${filters.adults}&children=${filters.children}&sort_by=${filters.sortBy}&currency=${filters.currency}`;
      console.log('[Travel] API URL:', url);
      
      const response = await fetch(url);
      
      console.log('[Travel] API Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch hotel suggestions: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('[Travel] API Response data:', data);
      
      const hotels = data.hotels || [];
      console.log('[Travel] Hotel count:', hotels.length);
      if (hotels.length > 0) {
        console.log('[Travel] First hotel object:', JSON.stringify(hotels[0], null, 2));
      }
      
      setHotelSuggestions(prev => new Map(prev).set(eventId, {
        eventId,
        hotels,
        loading: false,
      }));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to get hotel suggestions';
      console.error('[Travel] Error fetching hotels:', errorMsg);
      setHotelSuggestions(prev => new Map(prev).set(eventId, {
        eventId,
        hotels: [],
        loading: false,
        error: errorMsg,
      }));
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Upcoming Travel</h2>
          <p className="text-gray-500">Manage your travel plans for the next 1 year.</p>
        </div>
        <Button onClick={fetchTravelEvents} disabled={loading} className="flex items-center gap-2">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <p className="font-semibold">{error}</p>
          {error.includes('credentials') && (
            <div className="mt-3 text-xs">
              <p className="font-semibold mb-2">How to Enable Travel Access:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Go to <strong>Settings</strong> tab</li>
                <li>Click <strong>Connect Gmail</strong> or <strong>Upload Google Credentials</strong></li>
                <li>Select your Google credentials JSON file (with Calendar API enabled)</li>
                <li>Set your <strong>Home Location</strong> in Summary Preferences</li>
                <li>Return to Travel tab and click <strong>Refresh</strong></li>
              </ol>
            </div>
          )}
        </div>
      )}

      {!error && !loading && !homeLocation && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
          <p className="font-semibold">⚠️ Home Location Not Set</p>
          <p className="mt-2">To filter events by distance (100+ miles), please set your home location in <strong>Settings → Summary Preferences → Home Location</strong>.</p>
        </div>
      )}

      {loading ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-gray-200 text-center">
          <div className="inline-block">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-indigo-600"></div>
          </div>
          <p className="mt-4 text-gray-600 font-medium">Loading travel events...</p>
        </div>
      ) : travelEvents.length === 0 && !error ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-gray-200 text-center">
          <svg className="h-12 w-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
          </svg>
          <p className="text-gray-500 text-lg font-semibold">No travel events found</p>
          <p className="text-gray-400 text-sm mt-2">You don't have any travel-related events scheduled in the next 1 year.</p>
          <Button onClick={fetchTravelEvents} className="mt-4">Check Calendar</Button>
        </div>
      ) : (
        <div className="space-y-6">
          {travelEvents.length > 0 && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900">
                Travel Events: <span className="text-amber-600">{travelEvents.length}</span>
              </h3>
              <p className="text-sm text-gray-600 mt-2">
                Found {travelEvents.length} travel-related event{travelEvents.length !== 1 ? 's' : ''} in the next 1 year
              </p>
            </div>
          )}

          <div className="space-y-4">
            {travelEvents.map((event) => (
              <div key={event.id} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                <div className="flex gap-4">
                  {/* Type Badge */}
                  <div className="flex flex-col items-center justify-center min-w-fit bg-amber-50 px-4 py-3 rounded-lg border border-amber-100">
                    <div className="text-xs font-semibold text-amber-700">{getTravelType(event)}</div>
                    <div className="text-sm font-bold text-amber-700 mt-2">{event.duration}d</div>
                  </div>

                  {/* Event Content */}
                  <div className="flex-1">
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="text-lg font-bold text-gray-900 flex-1">{event.title}</h4>
                      <span className="text-xs font-semibold bg-amber-100 text-amber-800 px-3 py-1 rounded-full whitespace-nowrap ml-2">
                        {formatDate(event.startTime)} - {formatDate(event.endTime)}
                      </span>
                    </div>

                    {event.description && (
                      <p className="text-sm text-gray-600 mb-3 line-clamp-2">{event.description}</p>
                    )}
                    
                    <div className="flex flex-wrap gap-4 text-sm text-gray-600 mt-3">
                      {event.location && (
                        <div className="flex items-center gap-1">
                          <svg className="h-4 w-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          <span className="font-medium text-gray-700">{event.location}</span>
                          {event.distance && (
                            <span className="text-amber-600 font-semibold ml-2">({event.distance} mi)</span>
                          )}
                        </div>
                      )}
                      
                      {event.organizer && (
                        <div className="flex items-center gap-1">
                          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                          <span>{event.organizer}</span>
                        </div>
                      )}
                    </div>

                    {event.attendees && event.attendees.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Attendees ({event.attendees.length})</p>
                        <div className="flex flex-wrap gap-2">
                          {event.attendees.map((attendee, idx) => (
                            <span key={idx} className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                              {attendee}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Hotel Suggestions */}
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <button
                        onClick={() => {
                          if (expandedEventId === event.id) {
                            setExpandedEventId(null);
                          } else {
                            setExpandedEventId(event.id);
                            fetchHotelSuggestions(event);
                          }
                        }}
                        className="inline-flex items-center gap-2 text-sm font-semibold text-amber-600 hover:text-amber-700 transition-colors"
                      >
                        <svg className={`h-4 w-4 transition-transform ${expandedEventId === event.id ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                        </svg>
                        Find Hotels
                      </button>

                      {expandedEventId === event.id && (
                        <div className="mt-4">
                          {/* Show booking dates */}
                          <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                            <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">Hotel Dates</p>
                            <p className="text-sm text-blue-900 font-medium">
                              {formatDate(event.startTime)} → {formatDate(event.endTime)}
                              <span className="text-xs text-blue-700 ml-2">({event.duration} night{event.duration !== 1 ? 's' : ''})</span>
                            </p>
                          </div>

                          {/* Search Filters */}
                          {(() => {
                            const f = getFiltersForEvent(event.id);
                            return (
                              <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Search Filters</p>
                                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                                  {/* Bedrooms */}
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Rooms</label>
                                    <select
                                      value={f.bedrooms}
                                      onChange={e => updateFilterForEvent(event.id, 'bedrooms', Number(e.target.value))}
                                      className="w-full text-sm border border-gray-300 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                                    >
                                      {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n} Room{n > 1 ? 's' : ''}</option>)}
                                    </select>
                                  </div>
                                  {/* Adults */}
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Adults</label>
                                    <select
                                      value={f.adults}
                                      onChange={e => updateFilterForEvent(event.id, 'adults', Number(e.target.value))}
                                      className="w-full text-sm border border-gray-300 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                                    >
                                      {[1, 2, 3, 4, 5, 6, 7, 8].map(n => <option key={n} value={n}>{n} Adult{n > 1 ? 's' : ''}</option>)}
                                    </select>
                                  </div>
                                  {/* Children */}
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Children</label>
                                    <select
                                      value={f.children}
                                      onChange={e => updateFilterForEvent(event.id, 'children', Number(e.target.value))}
                                      className="w-full text-sm border border-gray-300 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                                    >
                                      {[0, 1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n} {n === 1 ? 'Child' : 'Children'}</option>)}
                                    </select>
                                  </div>
                                  {/* Max Price */}
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Max Price/Night</label>
                                    <select
                                      value={f.maxPrice}
                                      onChange={e => updateFilterForEvent(event.id, 'maxPrice', Number(e.target.value))}
                                      className="w-full text-sm border border-gray-300 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                                    >
                                      {[50, 100, 150, 200, 300, 500, 750, 1000].map(p => <option key={p} value={p}>${p}</option>)}
                                    </select>
                                  </div>
                                  {/* Min Rating */}
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Min Rating</label>
                                    <select
                                      value={f.minRating}
                                      onChange={e => updateFilterForEvent(event.id, 'minRating', Number(e.target.value))}
                                      className="w-full text-sm border border-gray-300 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                                    >
                                      <option value={3.0}>3.0+ ★★★</option>
                                      <option value={3.5}>3.5+ ★★★½</option>
                                      <option value={4.0}>4.0+ ★★★★</option>
                                      <option value={4.5}>4.5+ ★★★★½</option>
                                    </select>
                                  </div>
                                  {/* Sort By */}
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Sort By</label>
                                    <select
                                      value={f.sortBy}
                                      onChange={e => updateFilterForEvent(event.id, 'sortBy', e.target.value)}
                                      className="w-full text-sm border border-gray-300 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                                    >
                                      <option value="rating">Best Rated</option>
                                      <option value="price">Lowest Price</option>
                                    </select>
                                  </div>
                                  {/* Currency */}
                                  <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Currency</label>
                                    <select
                                      value={f.currency}
                                      onChange={e => updateFilterForEvent(event.id, 'currency', e.target.value)}
                                      className="w-full text-sm border border-gray-300 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                                    >
                                      <option value="USD">USD ($)</option>
                                      <option value="EUR">EUR (€)</option>
                                      <option value="GBP">GBP (£)</option>
                                      <option value="CAD">CAD (CA$)</option>
                                      <option value="AUD">AUD (A$)</option>
                                    </select>
                                  </div>
                                </div>
                                <button
                                  onClick={() => fetchHotelSuggestions(event, true)}
                                  className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-amber-600 text-white text-sm font-semibold rounded hover:bg-amber-700 transition-colors"
                                >
                                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                  </svg>
                                  Search Hotels
                                </button>
                              </div>
                            );
                          })()}

                          {hotelSuggestions.get(event.id)?.loading ? (
                            <div className="text-center py-4">
                              <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-amber-600"></div>
                              <p className="text-sm text-gray-600 mt-2">Finding hotels...</p>
                            </div>
                          ) : hotelSuggestions.get(event.id)?.error ? (
                            <div className="text-center py-4">
                              <p className="text-sm text-red-600">{hotelSuggestions.get(event.id)?.error}</p>
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {hotelSuggestions.get(event.id)?.hotels && hotelSuggestions.get(event.id)!.hotels.length > 0 ? (
                                hotelSuggestions.get(event.id)!.hotels.map((hotel, idx) => (
                                  <div key={idx} className="bg-gradient-to-r from-amber-50 to-orange-50 p-4 rounded-lg border border-amber-200">
                                    <div className="flex justify-between items-start mb-1">
                                      <h5 className="font-bold text-gray-900 text-base leading-tight">{hotel.name}</h5>
                                      <div className="flex items-center gap-1 ml-2 shrink-0">
                                        <svg className="h-4 w-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                        </svg>
                                        <span className="text-sm font-semibold text-gray-700">{hotel.rating.toFixed(1)}</span>
                                      </div>
                                    </div>
                                    {/* Address line */}
                                    {hotel.address ? (
                                      <p className="text-xs text-gray-500 mb-1 flex items-center gap-1">
                                        <svg className="h-3 w-3 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                        </svg>
                                        {hotel.address}
                                      </p>
                                    ) : (
                                      <p className="text-xs text-gray-500 mb-1">{hotel.city}{hotel.country ? `, ${hotel.country}` : ''}</p>
                                    )}
                                    <div className="flex justify-between items-center mt-2">
                                      <div>
                                        <p className="text-lg font-bold text-amber-700">${hotel.price_per_night.toFixed(0)}</p>
                                        <p className="text-xs text-gray-600">per night · {hotel.bedrooms} room{hotel.bedrooms !== 1 ? 's' : ''}</p>
                                      </div>
                                    </div>

                                    {/* Booking Links */}
                                    <div className="mt-3 pt-3 border-t border-amber-100 flex flex-wrap gap-2">
                                      {hotel.url && (
                                        <a
                                          href={hotel.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center gap-1 px-4 py-2 bg-amber-600 text-white text-xs font-bold rounded hover:bg-amber-700 transition-colors shadow-sm"
                                          title="Book this hotel"
                                        >
                                          Book
                                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4m-4-4l-8-8m0 0h8m-8 8v8" />
                                          </svg>
                                        </a>
                                      )}
                                      {hotel.map_url && (
                                        <a
                                          href={hotel.map_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center gap-1 px-3 py-2 bg-purple-500 text-white text-xs font-semibold rounded hover:bg-purple-600 transition-colors"
                                          title="View on Map"
                                        >
                                          Map
                                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                                          </svg>
                                        </a>
                                      )}
                                    </div>
                                  </div>
                                ))
                              ) : (
                                <p className="text-sm text-gray-600 text-center py-4">No hotels found for this destination</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
