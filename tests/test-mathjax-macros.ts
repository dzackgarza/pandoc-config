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
    if (unknown.length)
      failures.push(`${call}: MathJax does not define ${unknown.join(", ")}`);
  } catch (error) {
    failures.push(`${call}: ${(error as Error).message}`);
  }
}
const series = await mathjax.tex2mmlPromise(String.raw`\fps{\frac{a}{b}}`);
for (const bracket of [
  /data-latex="\\left\\llbracket\s*">&#x27E6;<\/mo>/,
  /data-latex="\\right\\rrbracket\s*">&#x27E7;<\/mo>/,
])
  if (!bracket.test(series))
    failures.push(`\\fps{\\frac{a}{b}} lacks ${bracket}:\n${series}`);
const laurent = await mathjax.tex2mmlPromise(String.raw`\fls{\frac{a}{b}}`);
const delimiters = [...laurent.matchAll(/data-latex="(\\(?:left|right).)"/g)]
  .map((match) => match[1])
  .join(" ");
const sequence = String.raw`\left( \right. \left( \right) \left. \right)`;
if (delimiters !== sequence)
  failures.push(
    `\\fls{\\frac{a}{b}} sets ${delimiters}, not ${sequence}:\n${laurent}`,
  );
const diagonal = await mathjax.tex2mmlPromise(String.raw`\diagonal X`);
if (!/<mi[^>]*>X<\/mi>/.test(diagonal))
  failures.push(`\\diagonal X drops the X:\n${diagonal}`);
for (const failure of failures) console.log(failure);
const count = Object.keys(macros).length;
console.log(`${count - failures.length}/${count} macros typeset in MathJax.`);
process.exit(failures.length ? 1 : 0);
