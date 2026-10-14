// Typesets every generated macro with MathJax 4 and the TeX packages its
// consumers load (ams, mathtools, and stmaryrd from
// templates/js/mathjax-stmaryrd.js), and fails on a TeX error. A macro that
// LaTeX accepts but MathJax does not define renders as an error in every
// MathJax consumer. The Node entry point and tex2mmlPromise, which loads the
// extensions a formula autoloads, are MathJax's documented server use:
// https://docs.mathjax.org/en/latest/server/components.html
import MathJaxNode from "mathjax";
import "../templates/js/mathjax-stmaryrd.js";

declare global {
  var MathJax: { startup: { defaultReady(): void } };
  function registerStmaryrd(mathjax: typeof globalThis.MathJax): void;
}

// MathJax passes its TeX input jax to formatError; the test does not read it.
type TexInputJax = object;
type Macro = string | [string, number] | [string, number, string];
const macros: Record<string, Macro> = await Bun.file(
  `${import.meta.dir}/../templates/css/mathjax-macros.json`,
).json();
const mathjax = await MathJaxNode.init({
  loader: { load: ["input/tex", "[tex]/mathtools"] },
  startup: {
    ready() {
      registerStmaryrd(MathJax);
      MathJax.startup.defaultReady();
    },
  },
  tex: {
    packages: { "[+]": ["mathtools", "stmaryrd"] },
    macros,
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
for (const failure of failures) console.log(failure);
const count = Object.keys(macros).length;
console.log(`${count - failures.length}/${count} macros typeset in MathJax.`);
process.exit(failures.length ? 1 : 0);
