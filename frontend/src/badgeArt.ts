// Artwork for every badge: which compass direction it belongs to, which symbol it shows and how
// "deep" it is (1 bronze, 2 silver, 3 gold). Texts live in the locale files under badges.<code>.

export type BadgeGroup = 'general' | 'body' | 'sleep' | 'schedule' | 'calendar' | 'mind' | 'focus' | 'work' | 'groups'

// order of the sections on the badges page, and each section's colour
export const BADGE_GROUPS: { key: BadgeGroup; accent: string; direction: string }[] = [
  { key: 'general', accent: '--color-compass-north', direction: '' },
  { key: 'body', accent: '--color-teal-500', direction: 'n' },
  { key: 'sleep', accent: '--color-indigo-500', direction: 'ne' },
  { key: 'schedule', accent: '--color-pink-500', direction: 'e' },
  { key: 'calendar', accent: '--color-sky-500', direction: 'se' },
  { key: 'mind', accent: '--color-purple-500', direction: 's' },
  { key: 'focus', accent: '--color-amber-500', direction: 'sw' },
  { key: 'work', accent: '--color-orange-500', direction: 'w' },
  { key: 'groups', accent: '--color-green-500', direction: 'nw' },
]

// Line symbols on a 24x24 grid, drawn with currentColor
export const GLYPHS: Record<string, string> = {
  drop: '<path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11z"/><path d="M9 15a3 3 0 0 0 3 3"/>',
  heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
  sprout: '<path d="M12 21v-9"/><path d="M12 12c0-4 3-6 7-6 0 4-3 6-7 6z"/><path d="M12 14c0-3-2.5-5-6-5 0 3 2.5 5 6 5z"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="M7.5 12.5l3 3 6-6.5"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  star: '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.5 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/>',
  crown: '<path d="M4 8l4 4 4-7 4 7 4-4-2 11H6z"/>',
  flame: '<path d="M12 3c1 3 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-9z"/>',
  trophy: '<path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 6H5v1a3 3 0 0 0 3 3M16 6h3v1a3 3 0 0 1-3 3"/><path d="M12 13v4M8.5 20h7M10 17h4"/>',
  tomato: '<circle cx="12" cy="13.5" r="6.5"/><path d="M12 7c0-2 1-3 3-3M9.5 7.5C8 6 7 6.5 6.5 7M14.5 7.5c1.5-1.5 2.5-1 3-.5"/>',
  stopwatch: '<circle cx="12" cy="13.5" r="7"/><path d="M12 10v4l2.5 1.5M10 3h4M12 3v3.5"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
  sparkle: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 17l.7 1.8 1.8.7-1.8.7L19 22l-.7-1.8-1.8-.7 1.8-.7z"/>',
  gem: '<path d="M6 4h12l3 5-9 11L3 9z"/><path d="M3 9h18M9 4l-1 5 4 11M15 4l1 5-4 11"/>',
  planet: '<circle cx="12" cy="12" r="5"/><ellipse cx="12" cy="12" rx="10" ry="3.5" transform="rotate(-20 12 12)"/>',
  candle: '<rect x="9" y="10" width="6" height="10" rx="1"/><path d="M12 3c1.5 2 2 3 0 5-2-2-1.5-3 0-5z"/>',
  yin: '<circle cx="12" cy="12" r="9"/><path d="M12 3a4.5 4.5 0 0 1 0 9 4.5 4.5 0 0 0 0 9"/>',
  mountain: '<path d="M3 20l6-11 4 6 3-4 5 9z"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  wind: '<path d="M3 9h11a3 3 0 1 0-3-3M3 15h15a3 3 0 1 1-3 3M3 12h8"/>',
  dumbbell: '<path d="M6 8v8M3.5 10v4M18 8v8M20.5 10v4M6 12h12"/>',
  steps: '<path d="M8 4c2 0 3 2 3 4s-1 3-3 3-3-1.5-3-3.5S6 4 8 4zM6 14h5v2a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2zM16 8c2 0 3 2 3 4s-1 3-3 3-3-1.5-3-3.5S14 8 16 8zM14 18h5v1a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2z"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  bed: '<path d="M3 18V6M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5"/><circle cx="7" cy="11" r="1.6"/>',
  zzz: '<path d="M5 6h6l-6 6h6M13 12h5l-5 5h5"/>',
  book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11M9 8h6"/>',
  calendar: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
  pin: '<path d="M12 21v-6M8 4h8l-1 6 3 3H6l3-3z"/>',
  cake: '<rect x="4" y="13" width="16" height="7" rx="1.5"/><path d="M4 16.5c2 1.3 3.5 1.3 4 0 .5 1.3 3.5 1.3 4 0 .5 1.3 3.5 1.3 4 0M9 13v-3M15 13v-3M9 7.5v.5M15 7.5v.5"/>',
  briefcase: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
  brain: '<path d="M12 4a4 4 0 0 0-4 4 3 3 0 0 0-2 5 3 3 0 0 0 3 4 3 3 0 0 0 3 2zM12 4a4 4 0 0 1 4 4 3 3 0 0 1 2 5 3 3 0 0 1-3 4 3 3 0 0 1-3 2zM12 4v15"/>',
  face: '<circle cx="12" cy="12" r="9"/><path d="M8.5 14c1 1.5 2.2 2 3.5 2s2.5-.5 3.5-2"/><circle cx="9" cy="10" r=".8"/><circle cx="15" cy="10" r=".8"/>',
  map: '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14M15 6v14"/>',
  lotus: '<path d="M12 18c-4 0-7-2-8-6 3 0 5 1 6 3 0-4 1-7 2-9 1 2 2 5 2 9 1-2 3-3 6-3-1 4-4 6-8 6z"/>',
  hourglass: '<path d="M7 3h10M7 21h10M8 3c0 5 4 6 4 9s-4 4-4 9M16 3c0 5-4 6-4 9s4 4 4 9"/>',
  pen: '<path d="M4 20l1-4L16 5l3 3L8 19z"/><path d="M14 7l3 3"/>',
  books: '<path d="M5 4h4v16H5zM10 4h4v16h-4zM15.5 5.5l3.8-1 3 15-3.8 1z"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
  people: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.4"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6M15 14.5c3 0 6 1.7 6 5.5"/>',
  flag: '<path d="M5 21V4M5 5h12l-2 4 2 4H5"/>',
}

interface Art {
  group: BadgeGroup
  glyph: string
  tier: 1 | 2 | 3
}

const a = (group: BadgeGroup, glyph: string, tier: 1 | 2 | 3): Art => ({ group, glyph, tier })

export const BADGE_ART: Record<string, Art> = {
  // general
  first_checkin: a('general', 'sprout', 1),
  checkins_50: a('general', 'check', 1),
  checkins_100: a('general', 'target', 2),
  checkins_250: a('general', 'target', 2),
  checkins_500: a('general', 'star', 3),
  checkins_1000: a('general', 'crown', 3),
  streak_7: a('general', 'flame', 1),
  streak_30: a('general', 'trophy', 2),
  daily_3: a('general', 'candle', 1),
  daily_14: a('general', 'flame', 2),
  daily_60: a('general', 'yin', 2),
  daily_100: a('general', 'mountain', 3),
  daily_365: a('general', 'planet', 3),
  points_100: a('general', 'star', 1),
  points_500: a('general', 'compass', 2),
  points_1000: a('general', 'sparkle', 2),
  points_2500: a('general', 'gem', 3),
  points_5000: a('general', 'planet', 3),
  perfect_day: a('general', 'sparkle', 2),
  habit_collector: a('general', 'folder', 2),
  all_four: a('general', 'wind', 2),
  // north: body & steps
  body_25: a('body', 'dumbbell', 2),
  steps_first: a('body', 'steps', 1),
  steps_7: a('body', 'steps', 2),
  steps_30: a('body', 'steps', 3),
  steps_20k: a('body', 'mountain', 3),
  steps_streak_7: a('body', 'flame', 2),
  weight_first: a('body', 'target', 1),
  weight_30: a('body', 'compass', 2),
  water_first: a('body', 'drop', 1),
  water_streak_7: a('body', 'drop', 2),
  workout_first: a('body', 'dumbbell', 1),
  workout_10: a('body', 'dumbbell', 2),
  workout_1200: a('body', 'stopwatch', 3),
  gratitude_first: a('mind', 'heart', 1),
  gratitude_30: a('mind', 'heart', 2),
  quest_first: a('general', 'target', 1),
  quest_7: a('general', 'map', 2),
  goal_first: a('general', 'flag', 1),
  goal_5: a('general', 'trophy', 2),
  wallpaper_first: a('general', 'gem', 1),
  wallpaper_5: a('general', 'gem', 3),
  group_habit_10: a('groups', 'people', 2),
  cheer_first: a('groups', 'sparkle', 1),
  cheer_10: a('groups', 'star', 2),
  // north-east: sleep
  sleep_first: a('sleep', 'moon', 1),
  sleep_7: a('sleep', 'bed', 2),
  sleep_30: a('sleep', 'zzz', 3),
  sleep_logged_14: a('sleep', 'book', 2),
  // east
  schedule_25: a('schedule', 'calendar', 2),
  // south-east: calendar
  notes_first: a('calendar', 'calendar', 1),
  notes_10: a('calendar', 'pin', 2),
  birthday_first: a('calendar', 'cake', 1),
  // south: mind
  mind_25: a('mind', 'brain', 2),
  mood_first: a('mind', 'face', 1),
  mood_7: a('mind', 'map', 2),
  mood_30: a('mind', 'compass', 3),
  meditation_first: a('mind', 'lotus', 1),
  meditation_10: a('mind', 'wind', 2),
  meditation_30: a('mind', 'yin', 3),
  meditation_100min: a('mind', 'hourglass', 2),
  journal_first: a('mind', 'book', 1),
  journal_10: a('mind', 'pen', 2),
  journal_30: a('mind', 'books', 3),
  journal_voice: a('mind', 'mic', 1),
  // south-west: focus
  first_pomodoro: a('focus', 'tomato', 1),
  pomodoro_10: a('focus', 'stopwatch', 1),
  pomodoro_50: a('focus', 'gear', 2),
  pomodoro_100: a('focus', 'target', 3),
  focus_600: a('focus', 'hourglass', 3),
  // west: work
  work_25: a('work', 'briefcase', 2),
  // north-west: groups
  group_join: a('groups', 'people', 1),
  group_create: a('groups', 'flag', 2),
  group_champion: a('groups', 'trophy', 3),
  challenge_first: a('groups', 'flag', 1),
  challenge_5: a('groups', 'trophy', 2),
}

export function artFor(code: string): Art | null {
  return BADGE_ART[code] ?? null
}

export const TIER_METAL: Record<1 | 2 | 3, { light: string; dark: string }> = {
  1: { light: '#e0a56b', dark: '#9a5f2c' }, // bronze
  2: { light: '#e4e9f0', dark: '#8993a3' }, // silver
  3: { light: '#f6dc7c', dark: '#b98a12' }, // gold
}
