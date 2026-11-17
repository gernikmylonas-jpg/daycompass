// Arrow-key navigation for a group of role="radio" buttons (ARIA radio group pattern):
// arrows / Home / End move focus and select; only the checked radio is in the tab order.
export function radioKeydown(ev: KeyboardEvent) {
  const keys = ['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft', 'Home', 'End']
  if (!keys.includes(ev.key)) return
  const group = (ev.currentTarget as HTMLElement).closest('[role="radiogroup"]')
  if (!group) return
  const radios = [...group.querySelectorAll<HTMLElement>('[role="radio"]')]
  const current = radios.indexOf(ev.currentTarget as HTMLElement)
  if (current < 0) return

  let next = current
  if (ev.key === 'Home') next = 0
  else if (ev.key === 'End') next = radios.length - 1
  else if (ev.key === 'ArrowDown' || ev.key === 'ArrowRight') next = (current + 1) % radios.length
  else next = (current - 1 + radios.length) % radios.length

  ev.preventDefault()
  radios[next].focus()
  radios[next].click()
}
