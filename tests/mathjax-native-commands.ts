import { previewMathJax, undefinedCommands } from "./preview-mathjax.ts";

const names: string[] = JSON.parse(await Bun.stdin.text());
const mathjax = await previewMathJax(false);
const native: string[] = [];
for (const name of names) {
  try {
    const mml = await mathjax.tex2mmlPromise(`\\${name}`);
    if (!undefinedCommands(mml).includes(`\\${name}`)) native.push(name);
  } catch (error) {
    if (!/^Missing argument for /.test((error as Error).message)) throw error;
    native.push(name);
  }
}
console.log(JSON.stringify(native));
