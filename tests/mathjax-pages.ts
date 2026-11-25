import { previewMathJax, undefinedCommands } from "./preview-mathjax.ts";

const formulas: string[] = JSON.parse(await Bun.stdin.text());
const directory = process.argv[2];
const mathjax = await previewMathJax(true, ["output/svg"]);
const undefinedIn = formulas
  .map((formula) => [formula, undefinedCommands(mathjax.tex2mml(formula))] as const)
  .filter(([, commands]) => commands.length > 0);
if (undefinedIn.length > 0) {
  for (const [formula, commands] of undefinedIn) {
    console.error(`${formula}: MathJax has no ${commands.join(", ")}`);
  }
  process.exit(1);
}
for (const [index, formula] of formulas.entries()) {
  const node = await mathjax.tex2svgPromise(formula, { display: true });
  await Bun.write(`${directory}/${index}.svg`, mathjax.startup.adaptor.innerHTML(node));
}
