
local ref_prefixes = {
  thm=true, lem=true, prop=true, cor=true, def=true, rmk=true, ex=true,
  conj=true, clm=true, obs=true, qst=true, prob=true, ass=true,
  warn=true, exr=true, cons=true, ["not"]=true, conv=true
}

local function is_latex_output()
  return FORMAT:match 'latex' or FORMAT:match 'pdf' or FORMAT:match 'beamer'
end

local function is_theorem_key(key)
  local prefix = key:match("^(%a+):.")
  return prefix ~= nil and ref_prefixes[prefix] == true
end

local function is_plain(citation)
  return #citation.prefix == 0 and #citation.suffix == 0
    and citation.mode ~= "SuppressAuthor"
end

function Cite(el)
  if not is_latex_output() then
    return nil
  end
  local has_theorem_key = false
  local all_plain = true
  for _, citation in ipairs(el.citations) do
    if is_theorem_key(citation.id) then
      has_theorem_key = true
      all_plain = all_plain and is_plain(citation)
    else
      all_plain = false
    end
  end
  if not has_theorem_key then
    return nil
  end

  if all_plain then
    local keys = {}
    for _, citation in ipairs(el.citations) do
      table.insert(keys, citation.id)
    end
    return pandoc.RawInline('latex', "\\cref{" .. table.concat(keys, ",") .. "}")
  end

  local out = pandoc.Inlines{}
  local run = {}
  local bibliography_run = {}
  local previous = nil
  local function separator(kind)
    if previous == "theorem" and kind == "theorem" then
      out:insert(pandoc.Str(";"))
      out:insert(pandoc.Space())
    elseif previous ~= nil then
      out:insert(pandoc.Space())
    end
    previous = kind
  end
  local function flush_run()
    if #run > 0 then
      separator("theorem")
      out:insert(pandoc.RawInline('latex', "\\cref{" .. table.concat(run, ",") .. "}"))
      run = {}
    end
  end
  local function flush_bibliography_run()
    if #bibliography_run > 0 then
      separator("bibliography")
      out:insert(pandoc.Cite({}, bibliography_run))
      bibliography_run = {}
    end
  end
  for _, citation in ipairs(el.citations) do
    if not is_theorem_key(citation.id) then
      flush_run()
      table.insert(bibliography_run, citation)
    elseif is_plain(citation) then
      flush_bibliography_run()
      table.insert(run, citation.id)
    else
      flush_run()
      flush_bibliography_run()
      separator("theorem")
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
  flush_bibliography_run()
  return out
end

function Div(el)
  local envs = {
    theorem=true, lemma=true, proposition=true, corollary=true,
    proof=true, remark=true, definition=true, example=true,
    conjecture=true, claim=true, observation=true, question=true,
    problem=true, assumption=true, warning=true, exercise=true,
    construction=true, notation=true, convention=true
  }

  local env = el.classes[1]
  if not (env and envs[env]) then
    return el
  end

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
      beginString = beginString .. "\\label{" .. el.identifier .. "}"
    end

    local out = {pandoc.RawBlock('latex', beginString)}
    for _, block in ipairs(el.content) do
      table.insert(out, block)
    end
    table.insert(out, pandoc.RawBlock('latex', "\\end{" .. env .. "}"))
    return out
  else
    el.classes[#el.classes+1] = "proofenv"
    return el
  end
end

