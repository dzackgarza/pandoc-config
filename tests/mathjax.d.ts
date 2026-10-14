// The part of MathJax's Node entry point that the tests use:
// https://docs.mathjax.org/en/latest/server/components.html
declare module "mathjax" {
  interface MathJaxRuntime {
    tex2mmlPromise(tex: string, options?: { display: boolean }): Promise<string>;
  }
  const MathJax: { init(config: object): Promise<MathJaxRuntime> };
  export default MathJax;
}
