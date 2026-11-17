// Shared look-up tables for the 1-10 mood scale.
export const MOOD_EMOJI = ['😭', '😢', '😞', '😕', '😐', '🙂', '😊', '😄', '😁', '🤩']

/** red (1) -> amber -> green (10) */
export const moodHue = (score: number) => Math.round(((score - 1) / 9) * 125)
export const moodFill = (score: number) => `hsl(${moodHue(score)} 72% 46%)`
/** text colour that stays readable on moodFill */
export const moodInk = (score: number) => {
  const h = moodHue(score)
  return h >= 38 && h <= 105 ? '#111827' : '#ffffff'
}
