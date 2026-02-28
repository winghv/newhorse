import { describe, it, expect } from "vitest";
import en from "../../messages/en.json";
import zh from "../../messages/zh.json";

function flattenKeys(obj: Record<string, any>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([key, val]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof val === "object" && val !== null) {
      return flattenKeys(val, path);
    }
    return [path];
  });
}

describe("i18n message completeness", () => {
  const enKeys = flattenKeys(en);
  const zhKeys = flattenKeys(zh);

  it("en and zh have the same number of keys", () => {
    expect(enKeys.length).toBe(zhKeys.length);
  });

  it("every en key exists in zh", () => {
    const zhSet = new Set(zhKeys);
    const missing = enKeys.filter((k) => !zhSet.has(k));
    expect(missing).toEqual([]);
  });

  it("every zh key exists in en", () => {
    const enSet = new Set(enKeys);
    const missing = zhKeys.filter((k) => !enSet.has(k));
    expect(missing).toEqual([]);
  });
});
