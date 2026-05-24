/**
 * Helpers for formatting hours_json and computing "open now" state.
 *
 * The schema we store is { mon: "10:00-21:00", ..., sun: "11:00-19:00" } —
 * empty string or null means closed that day.
 *
 * When hours_json is null (data not yet sourced), we render "—".
 */

export type Hours = Record<string, string | null>;

const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
export type DayKey = (typeof DAY_ORDER)[number];

const DAY_LABEL: Record<DayKey, string> = {
  mon: "Mon",
  tue: "Tue",
  wed: "Wed",
  thu: "Thu",
  fri: "Fri",
  sat: "Sat",
  sun: "Sun",
};

export function todayKey(): DayKey {
  // JS getDay(): 0=Sun, 1=Mon, ..., 6=Sat. Map to our keys.
  const jsDay = new Date().getDay();
  const order: DayKey[] = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  return order[jsDay];
}

export function isOpenNow(hours: Hours | null): boolean | null {
  if (!hours) return null;
  const today = hours[todayKey()];
  if (!today) return false;
  const m = today.match(/^(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})$/);
  if (!m) return null;
  const [, oh, om, ch, cm] = m;
  const now = new Date();
  const nowMin = now.getHours() * 60 + now.getMinutes();
  const openMin = Number(oh) * 60 + Number(om);
  const closeMin = Number(ch) * 60 + Number(cm);
  return nowMin >= openMin && nowMin <= closeMin;
}

export function formatHoursList(hours: Hours | null): { day: string; time: string }[] {
  if (!hours) return [];
  return DAY_ORDER.map((d) => ({
    day: DAY_LABEL[d],
    time: hours[d] ?? "Closed",
  }));
}

export function todaysHours(hours: Hours | null): string | null {
  if (!hours) return null;
  return hours[todayKey()] ?? null;
}
