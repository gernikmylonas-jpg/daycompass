// Member pictures are fetched as blobs. Keep each for a short while only, so a changed or un-shared picture soon
// disappears for other people, release the memory, and forget everything when someone logs out.
const TTL_MS = 60_000
const cache = new Map<string, { url: string; at: number }>()

export const cachedAvatar = (id: string): string | null => {
  const hit = cache.get(id)
  if (!hit) return null
  if (Date.now() - hit.at > TTL_MS) { URL.revokeObjectURL(hit.url); cache.delete(id); return null }
  return hit.url
}
export const rememberAvatar = (id: string, blob: Blob): string => {
  const old = cache.get(id)
  if (old) URL.revokeObjectURL(old.url)
  const url = URL.createObjectURL(blob)
  cache.set(id, { url, at: Date.now() })
  return url
}
export const clearAvatars = () => {
  for (const { url } of cache.values()) URL.revokeObjectURL(url)
  cache.clear()
}
