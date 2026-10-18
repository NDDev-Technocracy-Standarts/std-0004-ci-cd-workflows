// Smallest module that still gives bun something real to run.
export function checksum(text) {
  return [...new TextEncoder().encode(text)].reduce((a, b) => a + b, 0) % 256;
}
