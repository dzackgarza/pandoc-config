import { previewMathJax } from "./preview-mathjax.ts";

const formulas: string[] = JSON.parse(await Bun.stdin.text());
const directory = process.argv[2];
const mathjax = await previewMathJax(true, ["output/svg"]);
for (const [index, formula] of formulas.entries()) {
  const node = await mathjax.tex2svgPromise(formula, { display: true });
  await Bun.write(`${directory}/${index}.svg`, mathjax.startup.adaptor.innerHTML(node));
}
