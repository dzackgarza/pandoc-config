globalThis.registerStmaryrd = (MathJax) => {
  const { CharacterMap, DelimiterMap } = MathJax._.input.tex.TokenMap;
  const { Configuration } = MathJax._.input.tex.Configuration;
  const ParseMethods = MathJax._.input.tex.ParseMethods.default;
  new DelimiterMap("stmaryrd-delimiters", ParseMethods.delimiter, {
    "\\llbracket": "⟦",
    "\\rrbracket": "⟧",
  });
  new CharacterMap("stmaryrd-symbols", ParseMethods.mathchar0mo, {
    llbracket: "⟦",
    rrbracket: "⟧",
    mapsfrom: "↤",
  });
  new CharacterMap("stmaryrd-ordinary", ParseMethods.mathchar0mi, {
    lightning: "↯",
  });
  Configuration.create("stmaryrd", {
    handler: {
      delimiter: ["stmaryrd-delimiters"],
      macro: ["stmaryrd-symbols", "stmaryrd-ordinary"],
    },
  });
};
