// The steps of the first-visit tour. Each step may point at an element marked with data-tour="…" in the page;
// a step without a target is shown in the middle of the screen. Texts live in the locale files under
// tour.steps.<id>.{title,text}, so adding a step means: add it here, add the data-tour mark to the element,
// add its two texts to all four languages (a test checks this).
export interface TourStep {
  id: string
  target?: string // value of data-tour on the element to highlight
  round?: boolean // highlight with a circle (the compass and its buttons) instead of a rounded box
}

export const TOUR_STEPS: TourStep[] = [
  { id: 'welcome' },
  { id: 'compass', target: 'compass', round: true },
  { id: 'n', target: 'dir-n', round: true },
  { id: 'ne', target: 'dir-ne', round: true },
  { id: 'e', target: 'dir-e', round: true },
  { id: 'se', target: 'dir-se', round: true },
  { id: 's', target: 'dir-s', round: true },
  { id: 'sw', target: 'dir-sw', round: true },
  { id: 'w', target: 'dir-w', round: true },
  { id: 'nw', target: 'dir-nw', round: true },
  { id: 'center', target: 'center', round: true },
  { id: 'chip', target: 'chip' },
  { id: 'settings', target: 'settings' },
  { id: 'language', target: 'language' },
  { id: 'guide', target: 'guide' },
  { id: 'done' },
]
