--[==[
math-macros.lua — removes the macro definitions of templates/css/math-macros.md
from the document.

That file is the first input of an export whose writer has no template of
this directory that loads the macros (docx, odt, epub, JATS, ConTeXt, ...).
The `latex_macros` extension of the Markdown reader applies each
`\newcommand` of it to the TeX math of the inputs after it, so the writer
gets the expansion of each macro. The definitions themselves are raw TeX in
a fenced div of the class `math-macros`; a writer that keeps raw TeX
(ConTeXt, Markdown, reStructuredText) would write them into its output.
]==]

function Div(div)
  if div.classes:includes('math-macros') then
    return {}
  end
end
