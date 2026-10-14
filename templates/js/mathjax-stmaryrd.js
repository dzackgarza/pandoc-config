// The MathJax 4 TeX package "stmaryrd": the stmaryrd delimiters \llbracket and
// \rrbracket, which MathJax does not define. MathJax 4's default font, New
// Computer Modern, has stretchy glyphs for them (U+27E6, U+27E7), so
// \left\llbracket ... \right\rrbracket sizes as it does in LaTeX.
//
// The registration follows MathJax's custom TeX extension demo:
// https://github.com/mathjax/MathJax-demos-web/tree/master/custom-tex-extension
// Call registerStmaryrd(MathJax) in startup.ready before
// MathJax.startup.defaultReady(), and add "stmaryrd" to tex.packages.
globalThis.registerStmaryrd = (MathJax) => {
  const { CharacterMap, DelimiterMap } = MathJax._.input.tex.TokenMap;
  const { Configuration } = MathJax._.input.tex.Configuration;
  const ParseMethods = MathJax._.input.tex.ParseMethods.default;
  new DelimiterMap("stmaryrd-delimiters", ParseMethods.delimiter, {
    "\\llbracket": "\u27E6",
    "\\rrbracket": "\u27E7",
  });
  new CharacterMap("stmaryrd-symbols", ParseMethods.mathchar0mo, {
    llbracket: "\u27E6",
    rrbracket: "\u27E7",
  });
  Configuration.create("stmaryrd", {
    handler: {
      delimiter: ["stmaryrd-delimiters"],
      macro: ["stmaryrd-symbols"],
    },
  });
};
