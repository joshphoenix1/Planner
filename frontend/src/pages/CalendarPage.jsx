import { useState, useMemo } from 'react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, isToday, addMonths, subMonths, parseISO } from 'date-fns';
import { formatInTimeZone, toZonedTime } from 'date-fns-tz';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import Modal from '../components/Modal';
import styles from './CalendarPage.module.css';

const NZT = 'Pacific/Auckland';

function formatNZT(dateString, formatStr) {
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return formatInTimeZone(date, NZT, formatStr);
  } catch {
    return '';
  }
}

function parseNZT(dateString) {
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return toZonedTime(date, NZT);
  } catch {
    return new Date();
  }
}

export default function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const { data: status } = useApi(() => api.getGmailStatus());
  const { data: events, refetch } = useApi(() => api.getCalendarEvents());

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.syncCalendar();
      refetch();
    } finally {
      setSyncing(false);
    }
  };

  const days = useMemo(() => {
    const start = startOfMonth(currentMonth);
    const end = endOfMonth(currentMonth);
    return eachDayOfInterval({ start, end });
  }, [currentMonth]);

  const getEventsForDay = (day) => {
    return events?.filter(event => {
      const eventDate = parseNZT(event.start_time);
      return isSameDay(eventDate, day);
    }) || [];
  };

  const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));

  if (!status?.authenticated) {
    return (
      <div className={styles.page}>
        <h1>Calendar</h1>
        <div className={styles.setup}>
          <p>Connect your Gmail account first to sync calendar events.</p>
          <a href="/gmail" className={styles.link}>Go to Gmail Integration</a>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Calendar</h1>
        <button onClick={handleSync} disabled={syncing} className={styles.syncBtn}>
          {syncing ? 'Syncing...' : 'Sync Calendar'}
        </button>
      </header>

      <div className={styles.calendar}>
        <div className={styles.calendarHeader}>
          <button onClick={prevMonth} className={styles.navBtn}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <h2>{format(currentMonth, 'MMMM yyyy')}</h2>
          <button onClick={nextMonth} className={styles.navBtn}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        </div>

        <div className={styles.weekdays}>
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className={styles.weekday}>{day}</div>
          ))}
        </div>

        <div className={styles.days}>
          {/* Empty cells for days before the first of the month */}
          {Array.from({ length: days[0]?.getDay() || 0 }).map((_, i) => (
            <div key={`empty-${i}`} className={styles.emptyDay} />
          ))}

          {days.map(day => {
            const dayEvents = getEventsForDay(day);
            return (
              <div
                key={day.toISOString()}
                className={`${styles.day} ${isToday(day) ? styles.today : ''}`}
              >
                <span className={styles.dayNumber}>{format(day, 'd')}</span>
                <div className={styles.dayEvents}>
                  {dayEvents.slice(0, 3).map(event => (
                    <div
                      key={event.id}
                      className={styles.event}
                      onClick={() => setSelectedEvent(event)}
                    >
                      <span className={styles.eventTime}>
                        {event.all_day ? 'All day' : formatNZT(event.start_time, 'h:mm a')}
                      </span>
                      <span className={styles.eventTitle}>{event.title}</span>
                    </div>
                  ))}
                  {dayEvents.length > 3 && (
                    <div className={styles.moreEvents}>
                      +{dayEvents.length - 3} more
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className={styles.upcoming}>
        <h3>Upcoming Events</h3>
        <div className={styles.eventList}>
          {events?.slice(0, 10).map(event => (
            <div
              key={event.id}
              className={styles.upcomingEvent}
              onClick={() => setSelectedEvent(event)}
            >
              <div className={styles.eventDate}>
                <span className={styles.eventDay}>{formatNZT(event.start_time, 'd')}</span>
                <span className={styles.eventMonth}>{formatNZT(event.start_time, 'MMM')}</span>
              </div>
              <div className={styles.eventInfo}>
                <div className={styles.eventTitle}>{event.title}</div>
                <div className={styles.eventMeta}>
                  {event.all_day ? 'All day' : (
                    `${formatNZT(event.start_time, 'h:mm a')} - ${formatNZT(event.end_time, 'h:mm a')} NZT`
                  )}
                  {event.location && ` • ${event.location}`}
                </div>
              </div>
              {event.meeting_link && (
                <a
                  href={event.meeting_link}
                  target="_blank"
                  rel="noopener"
                  className={styles.meetLink}
                  onClick={e => e.stopPropagation()}
                >
                  Join
                </a>
              )}
            </div>
          ))}
          {(!events || events.length === 0) && (
            <p className={styles.empty}>No events synced yet.</p>
          )}
        </div>
      </div>

      {selectedEvent && (
        <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
      )}
    </div>
  );
}

function EventModal({ event, onClose }) {
  const attendees = event.attendees ? JSON.parse(event.attendees) : [];

  return (
    <Modal onClose={onClose} title={event.title || '(No Title)'}>
      <div className={styles.eventDetail}>
        <div className={styles.detailRow}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <span>
            {event.all_day ? 'All day' : (
              `${formatNZT(event.start_time, 'MMM d, h:mm a')} - ${formatNZT(event.end_time, 'h:mm a')} NZT`
            )}
          </span>
        </div>

        {event.location && (
          <div className={styles.detailRow}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 1118 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
            <span>{event.location}</span>
          </div>
        )}

        {event.meeting_link && (
          <div className={styles.detailRow}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 10l5-5m0 0v6m0-6h-6" />
              <path d="M10 14a3.5 3.5 0 005 0 3.5 3.5 0 000-5L9 3a3.5 3.5 0 00-5 0 3.5 3.5 0 000 5l6 6" />
            </svg>
            <a href={event.meeting_link} target="_blank" rel="noopener">
              Join Meeting
            </a>
          </div>
        )}

        {attendees.length > 0 && (
          <div className={styles.attendees}>
            <h4>Attendees ({attendees.length})</h4>
            <ul>
              {attendees.map((email, i) => (
                <li key={i}>{email}</li>
              ))}
            </ul>
          </div>
        )}

        {event.description && (
          <div className={styles.description}>
            <h4>Description</h4>
            <p>{event.description}</p>
          </div>
        )}
      </div>
    </Modal>
  );
}
