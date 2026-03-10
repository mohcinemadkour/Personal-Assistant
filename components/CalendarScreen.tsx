import React, { useState, useEffect } from 'react';
import { CalendarEvent } from '../types';
import { Button } from './Button';

interface CalendarScreenProps {
  onBack?: () => void;
}

export const CalendarScreen: React.FC<CalendarScreenProps> = ({ onBack }) => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'time' | 'title'>('time');

  useEffect(() => {
    fetchCalendarEvents();
  }, []);

  const fetchCalendarEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/calendar/events');
      const data = await response.json();
      
      if (!response.ok) {
        // Extract error message from response
        const errorMsg = data.error || response.statusText;
        if (response.status === 401) {
          throw new Error(
            `Google credentials not configured. Please upload your Google credentials in Settings to access your calendar.`
          );
        }
        throw new Error(`Failed to fetch calendar events: ${errorMsg}`);
      }
      
      setEvents(data.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch calendar events');
      console.error('Calendar fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const sortedEvents = [...events].sort((a, b) => {
    if (sortBy === 'time') {
      return new Date(a.startTime).getTime() - new Date(b.startTime).getTime();
    } else {
      return a.title.localeCompare(b.title);
    }
  });

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">My Calendar</h2>
          <p className="text-gray-500">Your upcoming events and schedule.</p>
        </div>
        <Button onClick={fetchCalendarEvents} disabled={loading} className="flex items-center gap-2">
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
              <p className="font-semibold mb-2">How to Enable Calendar Access:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Go to <strong>Settings</strong> tab</li>
                <li>Click <strong>Connect Gmail</strong> or <strong>Upload Google Credentials</strong></li>
                <li>Select your Google credentials JSON file (with Calendar API enabled)</li>
                <li>Return to Calendar tab and click <strong>Refresh</strong></li>
              </ol>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-gray-200 text-center">
          <div className="inline-block">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-indigo-600"></div>
          </div>
          <p className="mt-4 text-gray-600 font-medium">Loading calendar events...</p>
        </div>
      ) : events.length === 0 && !error ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-gray-200 text-center">
          <p className="text-gray-500">No upcoming events found.</p>
          <Button onClick={fetchCalendarEvents} className="mt-4">Try Again</Button>
        </div>
      ) : (
        <div className="space-y-6">
          {!error && events.length > 0 && (
            <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900">
                Events Found: <span className="text-indigo-600">{events.length}</span>
              </h3>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">Sort by:</label>
                <select 
                  value={sortBy} 
                  onChange={(e) => setSortBy(e.target.value as 'time' | 'title')}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="time">Date/Time</option>
                  <option value="title">Title</option>
                </select>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {sortedEvents.map((event) => (
              <div key={event.id} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                <div className="flex gap-4">
                  {/* Date/Time Badge */}
                  <div className="flex flex-col items-center justify-center min-w-fit bg-indigo-50 px-4 py-3 rounded-lg border border-indigo-100">
                    <div className="text-xs font-semibold text-indigo-600">{formatDate(event.startTime)}</div>
                    <div className="text-sm font-bold text-indigo-700 mt-1">{formatTime(event.startTime)}</div>
                  </div>

                  {/* Event Content */}
                  <div className="flex-1">
                    <h4 className="text-lg font-bold text-gray-900 mb-2">{event.title}</h4>
                    {event.description && (
                      <p className="text-sm text-gray-600 mb-3 line-clamp-2">{event.description}</p>
                    )}
                    
                    <div className="flex flex-wrap gap-4 text-sm text-gray-600 mt-3">
                      {event.location && (
                        <div className="flex items-center gap-1">
                          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          <span>{event.location}</span>
                        </div>
                      )}
                      
                      {event.organizer && (
                        <div className="flex items-center gap-1">
                          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>Organizer: {event.organizer}</span>
                        </div>
                      )}
                    </div>

                    {event.attendees && event.attendees.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Attendees</p>
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
