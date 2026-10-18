import { expect, test } from "bun:test";
import { checksum } from "./checksum.js";

test("checksum is stable", () => {
  expect(checksum("ci")).toBe(204);
  expect(checksum("")).toBe(0);
});

test("checksum stays in one byte", () => {
  for (const sample of ["", "a", "the quick brown fox"]) {
    expect(checksum(sample)).toBeGreaterThanOrEqual(0);
    expect(checksum(sample)).toBeLessThanOrEqual(255);
  }
});
