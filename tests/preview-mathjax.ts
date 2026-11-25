import { runInNewContext } from "node:vm";
import MathJaxNode from "mathjax";

type TexInputJax = object;
export type Macro = string | [string, number] | [string, number, string];
type PreviewConfig = {
  loader: { load?: string[] };
  tex: {
    macros: Record<string, Macro>;
    mathtools: { pairedDelimiters: Record<string, string[]> };
  };
  startup?: { ready(): void };
};

function previewConfig(): PreviewConfig {
  const rendered = Bun.spawnSync({
    cmd: [
      "pandoc",
      "-f",
      "markdown",
      "-t",
      "html5",
      "--standalone",
      `--template=${import.meta.dir}/../templates/pandoc_preview_template.html`,
      "--mathjax=https://cdn.jsdelivr.net/npm/mathjax@4/tex-chtml.js",
    ],
    stdin: Buffer.from(String.raw`$\fps{\frac{a}{b}}$`),
  });
  if (rendered.exitCode !== 0) throw new Error(rendered.stderr.toString());
  const script = [...rendered.stdout.toString().matchAll(/<script>([\s\S]*?)<\/script>/g)]
    .map((match) => match[1])
    .find((body) => body.includes("window.MathJax ="));
  if (script === undefined) throw new Error("Missing preview MathJax configuration");
  const window: { MathJax?: PreviewConfig } = {};
  runInNewContext(script, { window, globalThis });
  if (window.MathJax === undefined) throw new Error("Missing preview MathJax config");
  return window.MathJax;
}

export async function previewMathJax(withMacros: boolean, output: string[] = []) {
  const preview = previewConfig();
  const tex: PreviewConfig["tex"] = JSON.parse(JSON.stringify(preview.tex));
  return MathJaxNode.init({
    ...preview,
    loader: {
      ...preview.loader,
      load: ["input/tex", ...output, ...(preview.loader.load ?? [])],
    },
    tex: {
      ...tex,
      macros: withMacros ? tex.macros : {},
      mathtools: {
        ...tex.mathtools,
        pairedDelimiters: withMacros ? tex.mathtools.pairedDelimiters : {},
      },
      formatError: (_jax: TexInputJax, error: Error) => {
        throw error;
      },
    },
  });
}

export function undefinedCommands(mml: string): string[] {
  return [...mml.matchAll(/<mtext mathcolor="red"[^>]*>(\\[A-Za-z]+)<\/mtext>/g)].map(
    (match) => match[1],
  );
}
