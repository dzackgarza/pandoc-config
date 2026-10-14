// Typesets every generated macro with MathJax 3 and the TeX packages its
// consumers load (ams, mathtools), and fails on a TeX error. A macro that
// LaTeX accepts but MathJax does not define renders as an error in every
// MathJax consumer. The Node entry point and tex2mmlPromise, which loads the
// extensions a formula autoloads, are MathJax's documented server use:
// https://docs.mathjax.org/en/v3.2/server/components.html
import MathJax from "mathjax@3";

type Macro = string | [string, number] | [string, number, string];
const macros: Record<string, Macro> = await Bun.file(
  `${import.meta.dir}/../templates/css/mathjax-macros.json`,
).json();
const mathjax = await MathJax.init({
  loader: { load: ["input/tex", "[tex]/mathtools"] },
  tex: {
    packages: { "[+]": ["mathtools"] },
    macros,
    formatError: (_jax: unknown, error: Error) => {
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
for (const failure of failures) console.log(failure);
const count = Object.keys(macros).length;
console.log(`${count - failures.length}/${count} macros typeset in MathJax.`);
process.exit(failures.length ? 1 : 0);
