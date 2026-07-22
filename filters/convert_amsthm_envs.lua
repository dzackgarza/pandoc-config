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
-- Authored citation text and mode are preserved:
--
-- [see @thm:key]           -->  see \cref{thm:key}
-- [@thm:key, part (ii)]    -->  \cref{thm:key}, part (ii)
-- [-@thm:key]              -->  \ref{thm:key}
--
-- Prefix inlines render before the reference, suffix inlines after it
-- (a pandoc suffix carries its own leading comma). SuppressAuthor
-- semantics: cleveref references have no author, so suppression maps
-- to suppressing cleveref's type name — [-@thm:key] emits \ref{thm:key}
-- (bare number, still hyperlinked), matching authored intent such as
-- "Torelli's theorem [-@thm:torelli]". In a multi-item cluster,
-- maximal runs of plain items (no prefix/suffix, not suppressed) merge
-- into one \cref{a,b} so cleveref's native conjunction survives; items
-- carrying text or suppression render individually, with segments
-- joined by "; " mirroring the authored cluster delimiter.
--
-- Citation clusters containing any non-theorem-family key (e.g.
-- [@Ols04, Lem. 7.1]) are passed through untouched for bibliography
-- processing. Proof divs are never labeled, even when an id is authored.
--
-- Div labeling is DELIBERATELY more permissive than citation rewriting:
-- any authored non-empty id that does not end in ':' becomes a \label
-- verbatim (e.g. ::: {.theorem #torelli} emits \label{torelli}), while
-- only family-prefixed keys (thm:/lem:/... per ref_prefixes) are
-- rewritten from @-citations to \cref. A generic id is therefore a
-- valid LaTeX target for hand-authored \cref/\ref but is invisible to
-- the editor's reference model (zettlr-pandoc's extract-references
-- indexes family-prefixed keys only) and to @-citation syntax. Authors
-- who want workspace navigation, completion, and rename must use
-- family-prefixed ids; bare ids are a LaTeX-only escape hatch kept for
-- legacy documents (issue zettlr-pandoc#5 item B22 records this
-- asymmetry as intended).
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

-- A citation is "plain" when it carries no authored text and no
-- suppression; only plain citations may merge into a shared \cref.
local function is_plain(citation)
  return #citation.prefix == 0 and #citation.suffix == 0
    and citation.mode ~= "SuppressAuthor"
end

function Cite(el)
  if not is_latex_output() then
    return nil
  end
  local all_plain = true
  for _, citation in ipairs(el.citations) do
    if not is_theorem_key(citation.id) then
      -- Mixed or bibliography cluster: leave the whole Cite untouched.
      return nil
    end
    if not is_plain(citation) then
      all_plain = false
    end
  end
  if #el.citations == 0 then
    return nil
  end

  if all_plain then
    local keys = {}
    for _, citation in ipairs(el.citations) do
      table.insert(keys, citation.id)
    end
    return pandoc.RawInline('latex', "\\cref{" .. table.concat(keys, ",") .. "}")
  end

  -- Faithful rendering: preserve each item's authored prefix/suffix and
  -- mode. Maximal runs of plain items still merge into one \cref so
  -- cleveref's native conjunction survives; segments join with "; ".
  local out = pandoc.Inlines{}
  local run = {}
  local first_segment = true
  local function separator()
    if first_segment then
      first_segment = false
    else
      out:insert(pandoc.Str(";"))
      out:insert(pandoc.Space())
    end
  end
  local function flush_run()
    if #run > 0 then
      separator()
      out:insert(pandoc.RawInline('latex', "\\cref{" .. table.concat(run, ",") .. "}"))
      run = {}
    end
  end
  for _, citation in ipairs(el.citations) do
    if is_plain(citation) then
      table.insert(run, citation.id)
    else
      flush_run()
      separator()
      for _, inline in ipairs(citation.prefix) do
        out:insert(inline)
      end
      if #citation.prefix > 0 then
        out:insert(pandoc.Space())
      end
      local command = citation.mode == "SuppressAuthor" and "\\ref{" or "\\cref{"
      out:insert(pandoc.RawInline('latex', command .. citation.id .. "}"))
      for _, inline in ipairs(citation.suffix) do
        out:insert(inline)
      end
    end
  end
  flush_run()
  return out
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

