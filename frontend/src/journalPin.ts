// The journal PIN lives only in memory (never in storage), so closing the tab locks the journal.
// The API client reads it to add the X-Journal-Pin header to journal requests.
let pin = ''

export const getJournalPin = () => pin
export const setJournalPin = (value: string) => {
  pin = value
}
