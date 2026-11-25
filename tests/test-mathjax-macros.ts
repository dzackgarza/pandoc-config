import { runInNewContext } from "node:vm";
import MathJaxNode from "mathjax";

type TexInputJax = object;
type Macro = string | [string, number] | [string, number, string];
const macros: Record<string, Macro> = await Bun.file(
  `${import.meta.dir}/../templates/css/mathjax-macros.json`,
).json();
const rendered = Bun.spawnSync({
  cmd: [
    "pandoc", "-f", "markdown", "-t", "html5", "--standalone",
    `--template=${import.meta.dir}/../templates/pandoc_preview_template.html`,
    "--mathjax=https://cdn.jsdelivr.net/npm/mathjax@4/tex-chtml.js",
  ],
  stdin: Buffer.from(String.raw`$\fps{\frac{a}{b}}$`),
});
if (rendered.exitCode !== 0) throw new Error(rendered.stderr.toString());
const script = [
  ...rendered.stdout.toString().matchAll(/<script>([\s\S]*?)<\/script>/g),
]
  .map((match) => match[1])
  .find((body) => body.includes("window.MathJax ="));
if (script === undefined)
  throw new Error("Missing preview MathJax configuration");
type PreviewConfig = {
  loader: { load?: string[] };
  tex: { macros: Record<string, Macro> };
  startup?: { ready(): void };
};
const window: { MathJax?: PreviewConfig } = {};
runInNewContext(script, { window, globalThis });
const preview = window.MathJax;
if (preview === undefined) throw new Error("Missing preview MathJax config");
const mathjax = await MathJaxNode.init({
  ...preview,
  loader: {
    ...preview.loader,
    load: ["input/tex", ...(preview.loader.load ?? [])],
  },
  tex: {
    ...preview.tex,
    formatError: (_jax: TexInputJax, error: Error) => {
      throw error;
    },
  },
});
const failures: string[] = [];
for (const [name, macro] of Object.entries(macros)) {
  const arity = typeof macro === "string" ? 0 : macro[1];
  const call = `\\${name}` + "{x}".repeat(arity);
  try {
    const mml = await mathjax.tex2mmlPromise(`\\left. ${call}{x} \\right.`, {
      display: true,
    });
    const undefinedCommands = [
      ...mml.matchAll(/<mtext mathcolor="red"[^>]*>(\\[A-Za-z]+)<\/mtext>/g),
    ].map((match) => match[1]);
    if (undefinedCommands.length)
      failures.push(
        `${call}: MathJax does not define ${undefinedCommands.join(", ")}`,
      );
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
