-- Get the directory of this script to find utilities.lua relatively
local script_dir = debug.getinfo(1, "S").source:match("@(.*)[\\/]") or "."
package.path = package.path .. ';' .. script_dir .. '/?.lua;'
require "utilities"

-- In markdown, changes
--
-- :::{.theorem title="abcde" ref=:thm:123"}
-- ...
-- :::
--
-- into
--
-- \begin{theorem}["abcde"]
-- \label{thm:123}
-- ...
-- \end{theorem}
--
-- Supports math within the title.
--
-- Also supports Zettlr/pandoc-crossref style authored syntax:
--
-- ::: {.theorem #thm:key title="abcde"}   -->  \begin{theorem}[abcde]\label{thm:key}
--
-- and converts theorem-family citations into cleveref references
-- BEFORE the natbib/biblatex writer can turn them into \autocite:
--
-- @thm:key                 -->  \cref{thm:key}
-- [@thm:a; @lem:b]         -->  \cref{thm:a,lem:b}
--
-- Citation clusters containing any non-theorem-family key (e.g.
-- [@Ols04, Lem. 7.1]) are passed through untouched for bibliography
-- processing. Proof divs are never labeled, even when an id is authored.
-- \cref requires cleveref, which is loaded unconditionally by
-- dzg-unified.sty (used by research_draft/koma-article/ams-article
-- templates) and by research_paper.tex directly.

-- Theorem-family citation prefixes (each must be followed by ':' and a
-- nonempty key to count as a reference).
local ref_prefixes = {
  thm=true, lem=true, prop=true, cor=true, def=true, rmk=true, ex=true,
  conj=true, clm=true, obs=true, qst=true, prob=true, ass=true,
  warn=true, exr=true
}

local function is_latex_output()
  return FORMAT:match 'latex' or FORMAT:match 'pdf' or FORMAT:match 'beamer'
end

-- A theorem-family reference key is "<prefix>:<nonempty rest>".
local function is_theorem_key(key)
  local prefix = key:match("^(%a+):.")
  return prefix ~= nil and ref_prefixes[prefix] == true
end

function Cite(el)
  if not is_latex_output() then
    return nil
  end
  local keys = {}
  for _, citation in ipairs(el.citations) do
    if not is_theorem_key(citation.id) then
      -- Mixed or bibliography cluster: leave the whole Cite untouched.
      return nil
    end
    table.insert(keys, citation.id)
  end
  if #keys == 0 then
    return nil
  end
  return pandoc.RawInline('latex', "\\cref{" .. table.concat(keys, ",") .. "}")
end

function Div(el)
  local envs = {
    theorem=true, lemma=true, proposition=true, corollary=true,
    proof=true, remark=true, definition=true, example=true,
    conjecture=true, claim=true, observation=true, question=true,
    problem=true, assumption=true, warning=true, exercise=true
  }
  
  local env = el.classes[1]
  if not (env and envs[env]) then
    return el
  end

  -- For markdown cleaning, just leave as-is
  if FORMAT:match 'markdown' then
    return el
  end

  if FORMAT:match 'latex' or FORMAT:match 'pdf' or FORMAT:match 'beamer' then
    local beginString = "\\begin{" .. env .. "}"
    if el.attributes["title"] ~= nil then 
      beginString = beginString .. "[" .. el.attributes["title"] .. "]"
    end
    if el.attributes["ref"] ~= nil then
      beginString = beginString .. "\\label{" .. el.attributes["ref"] .. "}"
    elseif env ~= "proof" and el.identifier ~= "" and not el.identifier:match(":$") then
      -- Explicit-id syntax: ::: {.theorem #thm:key}. Proof divs stay
      -- unlabeled; an empty-key id like "#thm:" defines no target.
      beginString = beginString .. "\\label{" .. el.identifier .. "}"
    end

    local out = {pandoc.RawBlock('latex', beginString)}
    for _, block in ipairs(el.content) do
      table.insert(out, block)
    end
    table.insert(out, pandoc.RawBlock('latex', "\\end{" .. env .. "}"))
    return out
  else
    -- For HTML and other formats, add proofenv class for CSS styling
    el.classes[#el.classes+1] = "proofenv" 
    return el
  end
end

