import React, { useState, useEffect } from 'react';
import { CalendarEvent } from '../types';
import { Button } from './Button';

interface TravelEvent extends CalendarEvent {
  duration: number; // in days
  isTravelEvent: boolean;
  distance?: number; // in miles
}

// Approximate coordinates for major US cities (latitude, longitude)
const CITY_COORDINATES: Record<string, { lat: number; lon: number }> = {
  'dallas': { lat: 32.7767, lon: -96.7970 },
  'houston': { lat: 29.7604, lon: -95.3698 },
  'austin': { lat: 30.2672, lon: -97.7431 },
  'san antonio': { lat: 29.4241, lon: -98.4936 },
  'fort worth': { lat: 32.7555, lon: -97.3308 },
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
  // Try to extract city from format like "City Name, State" or "City Name"
  const parts = location.split(',');
  const city = parts[0].trim().toLowerCase();
  return city;
}

export const TravelScreen: React.FC = () => {
  const [travelEvents, setTravelEvents] = useState<TravelEvent[]>([]);
  const [allEvents, setAllEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [homeLocation, setHomeLocation] = useState<string | null>(null);

  useEffect(() => {
    // Retrieve home location from localStorage (preferences)
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
    fetchTravelEvents();
  }, []);

  const fetchTravelEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/calendar/events?days=180');
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
        // Must have a location
        if (!event.location || event.location.trim() === '') {
          return false;
        }
        
        // If we have a home location, calculate distance
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
            }
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

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Upcoming Travel</h2>
          <p className="text-gray-500">Manage your travel plans for the next 6 months.</p>
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
          <p className="text-gray-400 text-sm mt-2">You don't have any travel-related events scheduled in the next 6 months.</p>
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
                Found {travelEvents.length} travel-related event{travelEvents.length !== 1 ? 's' : ''} in the next 6 months
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
