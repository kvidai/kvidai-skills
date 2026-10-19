import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";

const SKILLS_DIR = import.meta.dir;
const INDEX_PATH = join(SKILLS_DIR, "index.json");

function parseFrontmatter(source: string): Record<string, string> {
  if (!source.startsWith("---\n")) return {};
  const end = source.indexOf("\n---", 4);
  if (end === -1) return {};
  const block = source.slice(4, end);
  const out: Record<string, string> = {};
  const lines = block.split("\n");
  let currentKey: string | null = null;
  let foldedLines: string[] = [];
  const flush = () => {
    if (currentKey) {
      out[currentKey] = foldedLines.join(" ").trim();
      currentKey = null;
      foldedLines = [];
    }
  };
  for (const line of lines) {
    const m = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (m && !line.startsWith(" ")) {
      flush();
      const [, key, rest] = m;
      if (rest === ">" || rest === ">-" || rest === "|") {
        currentKey = key;
      } else {
        out[key] = rest.trim();
      }
    } else if (currentKey) {
      foldedLines.push(line.trim());
    }
  }
  flush();
  return out;
}

const skillDirs = readdirSync(SKILLS_DIR)
  .filter(
    (e) =>
      !e.startsWith(".") &&
      !e.endsWith(".ts") &&
      !e.endsWith(".json") &&
      statSync(join(SKILLS_DIR, e)).isDirectory(),
  )
  .sort();

const index: {
  version: number;
  skills: Array<{
    name: string;
    description: string;
    files: Array<{ path: string; sha256: string; bytes: number }>;
  }>;
} = JSON.parse(readFileSync(INDEX_PATH, "utf-8"));

describe("skills directory structure", () => {
  for (const dir of skillDirs) {
    const skillMd = join(SKILLS_DIR, dir, "SKILL.md");

    test(`${dir}: has SKILL.md`, () => {
      expect(existsSync(skillMd)).toBe(true);
    });

    test(`${dir}: SKILL.md has name and description frontmatter`, () => {
      const fm = parseFrontmatter(readFileSync(skillMd, "utf-8"));
      expect(fm.name).toBeTruthy();
      expect(fm.description).toBeTruthy();
    });

    test(`${dir}: frontmatter name matches directory name`, () => {
      const fm = parseFrontmatter(readFileSync(skillMd, "utf-8"));
      expect(fm.name).toBe(dir);
    });
  }
});

describe("skills/index.json", () => {
  test("version is 1", () => {
    expect(index.version).toBe(1);
  });

  test("lists every skill directory", () => {
    const indexNames = index.skills.map((s) => s.name).sort();
    expect(indexNames).toEqual(skillDirs);
  });

  test("each entry has non-empty name and description", () => {
    for (const skill of index.skills) {
      expect(skill.name.length).toBeGreaterThan(0);
      expect(skill.description.length).toBeGreaterThan(0);
    }
  });

  test("all referenced files exist", () => {
    for (const skill of index.skills) {
      for (const file of skill.files) {
        const filePath = join(SKILLS_DIR, skill.name, file.path);
        expect(existsSync(filePath)).toBe(true);
      }
    }
  });

  test("all referenced files have correct byte size", () => {
    for (const skill of index.skills) {
      for (const file of skill.files) {
        const buf = readFileSync(join(SKILLS_DIR, skill.name, file.path));
        expect(buf.byteLength).toBe(file.bytes);
      }
    }
  });

  test("all referenced files have correct sha256", () => {
    for (const skill of index.skills) {
      for (const file of skill.files) {
        const buf = readFileSync(join(SKILLS_DIR, skill.name, file.path));
        const hash = createHash("sha256").update(buf).digest("hex");
        expect(hash).toBe(file.sha256);
      }
    }
  });
});
