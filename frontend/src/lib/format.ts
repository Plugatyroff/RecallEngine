/** Turn plain text typed by the user into safe HTML (cards store HTML). */
export function textToHtml(text: string): string {
  return text
    .trim()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
}

/** A short "how long until" label, e.g. "10m", "6h", "2d", "3mo", "1.5y". */
export function formatInterval(fromIso: string | Date, toIso: string | Date): string {
  const minutes = (new Date(toIso).getTime() - new Date(fromIso).getTime()) / 60000;
  // Compare rounded values, so e.g. 23.6 hours shows as "1d" rather than "24h"
  if (minutes < 1) return 'now';
  if (Math.round(minutes) < 60) return `${Math.round(minutes)}m`;
  const hours = minutes / 60;
  if (Math.round(hours) < 24) return `${Math.round(hours)}h`;
  const days = hours / 24;
  if (Math.round(days) < 30) return `${Math.round(days)}d`;
  if (Math.round(days / 30) < 12) return `${Math.round(days / 30)}mo`;
  return `${Math.round((days / 365) * 10) / 10}y`;
}
