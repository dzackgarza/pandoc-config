// Typesets every generated macro using the MathJax 4 configuration in a
// Pandoc preview export, and fails on a TeX error. A macro that
// LaTeX accepts but MathJax does not define renders as an error in every
// MathJax consumer. The Node entry point and tex2mmlPromise, which loads the
// extensions a formula autoloads, are MathJax's documented server use:
// https://docs.mathjax.org/en/latest/server/components.html
import { runInNewContext } from "node:vm";
import MathJaxNode from "mathjax";

// MathJax passes its TeX input jax to formatError; the test does not read it.
type TexInputJax = object;
type Macro = string | [string, number] | [string, number, string];
const macros: Record<string, Macro> = await Bun.file(
  `${import.meta.dir}/../templates/css/mathjax-macros.json`,
).json();
// Use the configuration from a real Pandoc export, not a separate test-only
// registration of the TeX package. The Node component replaces the browser
// component for typesetting, but executes the export's startup callback.
const rendered = Bun.spawnSync({
  cmd: [
    "pandoc", "-f", "markdown", "-t", "html5", "--standalone",
    `--template=${import.meta.dir}/../templates/pandoc_preview_template.html`,
    "--mathjax=https://cdn.jsdelivr.net/npm/mathjax@4/tex-chtml.js",
  ],
  stdin: Buffer.from(String.raw`$\fps{\frac{a}{b}}$`),
});
if (rendered.exitCode !== 0) throw new Error(rendered.stderr.toString());
const script = rendered.stdout.toString().match(
  /<!--MATHJAX_MACROS_START-->\s*<script>([\s\S]*?)<\/script>/,
)?.[1];
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
  // One more argument than the macro takes serves aliases such as
  // \wh = \widehat, and \left. \right. serves aliases of \middle.
  const call = `\\${name}` + "{x}".repeat(arity);
  try {
    await mathjax.tex2mmlPromise(`\\left. ${call}{x} \\right.`, {
      display: true,
    });
  } catch (error) {
    failures.push(`${call}: ${(error as Error).message}`);
  }
}
// \fps sets its argument in the stmaryrd double brackets as \left and \right
// delimiters, which MathJax sizes to the argument.
const series = await mathjax.tex2mmlPromise(String.raw`\fps{\frac{a}{b}}`);
for (const bracket of [
  /data-latex="\\left\\llbracket\s*">&#x27E6;<\/mo>/,
  /data-latex="\\right\\rrbracket\s*">&#x27E7;<\/mo>/,
])
  if (!bracket.test(series))
    failures.push(`\\fps{\\frac{a}{b}} lacks ${bracket}:\n${series}`);
// \fls sets its four parentheses as three \left ... \right groups in sequence,
// none inside another, so MathJax sizes each one to the argument alone and
// the two parentheses of each side have the same height.
const laurent = await mathjax.tex2mmlPromise(String.raw`\fls{\frac{a}{b}}`);
const delimiters = [...laurent.matchAll(/data-latex="(\\(?:left|right).)"/g)]
  .map((match) => match[1])
  .join(" ");
const sequence = String.raw`\left( \right. \left( \right) \left. \right)`;
if (delimiters !== sequence)
  failures.push(
    `\\fls{\\frac{a}{b}} sets ${delimiters}, not ${sequence}:\n${laurent}`,
  );
for (const failure of failures) console.log(failure);
const count = Object.keys(macros).length;
console.log(`${count - failures.length}/${count} macros typeset in MathJax.`);
process.exit(failures.length ? 1 : 0);
