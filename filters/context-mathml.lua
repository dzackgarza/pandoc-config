--[==[
context-mathml.lua — gives ConTeXt each formula as MathML.

The ConTeXt writer of Pandoc writes TeX math as it is, and ConTeXt is no
LaTeX: `\operatorname`, `\mathsf`, `\genfrac`, `\textrm` and many other
commands of the macro expansions are undefined in it. Pandoc's texmath
converts the TeX of a formula to MathML (the same conversion that gives the
MathML of epub and JATS), and the `mathml` module of ConTeXt typesets
MathML (`\startmml ... \stopmml`, x-mathml.mkxl). The template
templates/pandoc_context_template.tex loads that module.

A formula that texmath cannot convert stops the export with the formula and
the cause; ConTeXt could not typeset its TeX either.
]==]

if FORMAT ~= 'context' then
  error('context-mathml.lua: the filter is for the ConTeXt writer, not for ' .. FORMAT)
end

function Math(math)
  local html = pandoc.write(
    pandoc.Pandoc({ pandoc.Plain({ math }) }),
    'html',
    { html_math_method = 'mathml' }
  )
  local mathml = html:match('<math.-</math>')
  if mathml == nil then
    error('context-mathml.lua: texmath cannot convert the formula ' .. math.text
      .. ' to MathML; run pandoc -t html --mathml on it for the cause')
  end
  -- The TeX annotation is no content of the formula; x-mathml typesets the
  -- presentation MathML inside <semantics> only without it.
  mathml = mathml:gsub('<annotation.-</annotation>', ''):gsub('</?semantics>', '')
  return pandoc.RawInline('context', '\\startmml ' .. mathml .. ' \\stopmml')
end
