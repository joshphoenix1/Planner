import { format, parseISO } from 'date-fns';
import { formatInTimeZone, toZonedTime } from 'date-fns-tz';

export const NZT = 'Pacific/Auckland';

export function formatDateNZT(dateString, formatStr = 'PPp') {
  if (!dateString) return '';
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return formatInTimeZone(date, NZT, formatStr);
  } catch {
    return dateString;
  }
}

export function formatTimeNZT(dateString) {
  return formatDateNZT(dateString, 'h:mm a');
}

export function formatDateOnlyNZT(dateString) {
  return formatDateNZT(dateString, 'MMM d, yyyy');
}

export function formatDateTimeNZT(dateString) {
  return formatDateNZT(dateString, 'MMM d, h:mm a');
}

export function formatShortTimeNZT(dateString) {
  return formatDateNZT(dateString, 'h:mm a');
}

export function parseToNZT(dateString) {
  if (!dateString) return null;
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return toZonedTime(date, NZT);
  } catch {
    return null;
  }
}
