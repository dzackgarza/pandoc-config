import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { type Macro, previewMathJax, undefinedCommands } from "./preview-mathjax.ts";

const macros: Record<string, Macro> = await Bun.file(
  `${import.meta.dir}/../templates/css/mathjax-macros.json`,
).json();
const mathjax = await previewMathJax(true);
const failures: string[] = [];
for (const [name, macro] of Object.entries(macros)) {
  const arity = typeof macro === "string" ? 0 : macro[1];
  const call = `\\${name}` + "{x}".repeat(arity);
  try {
    const mml = await mathjax.tex2mmlPromise(`\\left. ${call}{x} \\right.`, {
      display: true,
    });
    const unknown = undefinedCommands(mml);
    if (unknown.length) failures.push(`${call}: MathJax does not define ${unknown.join(", ")}`);
  } catch (error) {
    failures.push(`${call}: ${(error as Error).message}`);
  }
}
const series = await mathjax.tex2mmlPromise(String.raw`\fps{\frac{a}{b}}`);
for (const bracket of [
  /data-latex="\\left\\llbracket\s*">&#x27E6;<\/mo>/,
  /data-latex="\\right\\rrbracket\s*">&#x27E7;<\/mo>/,
])
  if (!bracket.test(series)) failures.push(`\\fps{\\frac{a}{b}} lacks ${bracket}:\n${series}`);
const laurent = await mathjax.tex2mmlPromise(String.raw`\fls{\frac{a}{b}}`);
const delimiters = [...laurent.matchAll(/data-latex="(\\(?:left|right).)"/g)]
  .map((match) => match[1])
  .join(" ");
const sequence = String.raw`\left( \right. \left( \right) \left. \right)`;
if (delimiters !== sequence)
  failures.push(`\\fls{\\frac{a}{b}} sets ${delimiters}, not ${sequence}:\n${laurent}`);
const diagonal = await mathjax.tex2mmlPromise(String.raw`\diagonal X`);
if (!/<mi[^>]*>X<\/mi>/.test(diagonal)) failures.push(`\\diagonal X drops the X:\n${diagonal}`);
const note = mkdtempSync(join(tmpdir(), "compile-html-math-"));
writeFileSync(join(note, "note.md"), "---\ntitle: t\n---\n\nLet $a \\coloneqq b$.\n");
writeFileSync(join(note, "empty.bib"), "");
const built = Bun.spawnSync({
  cmd: [
    "just",
    "--justfile",
    `${import.meta.dir}/../justfile`,
    "compile-html",
    "note.md",
    "note.html",
    "empty.bib",
  ],
  cwd: note,
  env: { ...process.env, SVG_DIR: join(note, "svg") },
});
if (built.exitCode !== 0) throw new Error(built.stderr.toString());
const page = readFileSync(join(note, "note.html"), "utf8");
rmSync(note, { recursive: true });
const inline = /<span class="math inline">\\\(([\s\S]*?)\\\)<\/span>/.exec(page);
if (inline === null) failures.push(`compile-html gives no inline math:\n${page}`);
else {
  const tex = inline[1].replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
  const definition = await mathjax.tex2mmlPromise(tex);
  if (/<merror|mathcolor="red"/.test(definition))
    failures.push(`compile-html math ${tex} does not typeset:\n${definition}`);
  if (!/<mo[^>]*>(?:&#x2254;|≔|:)<\/mo>/.test(definition))
    failures.push(`compile-html math ${tex} has no colon-equals:\n${definition}`);
}
for (const failure of failures) console.log(failure);
const count = Object.keys(macros).length;
console.log(`${count - failures.length}/${count} macros typeset in MathJax.`);
process.exit(failures.length ? 1 : 0);
