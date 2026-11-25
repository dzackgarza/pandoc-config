local environments = { "solution", "proof", "concept", "strategy", "flashcard" }

if not FORMAT:match "html" then
  return {}
end

local hide_proofs = false
local kill_proofs = false

local function read_settings(meta)
  hide_proofs = meta["hide_proofs"] ~= nil
  kill_proofs = meta["kill_proofs"] ~= nil
end

local function environment_of(el)
  for _, name in ipairs(environments) do
    if el.classes:includes(name) then
      return name
    end
  end
  return nil
end

local function hide(el)
  local env_name = environment_of(el)
  if not env_name then
    return el
  end
  if kill_proofs then
    pandoc.log.info("hide_solutions_html: " .. env_name .. " removed")
    return pandoc.RawBlock("html", "<div></div>")
  end
  if not hide_proofs then
    return el
  end
  pandoc.log.info("hide_solutions_html: " .. env_name .. " folded")
  el.content:insert(1, pandoc.RawBlock("html", "<details><summary><i>(Click to expand " .. env_name .. ")</i></summary>"))
  el.content:insert(pandoc.RawBlock("latex", "\\begin{" .. env_name .. "}"))
  el.content:insert(pandoc.RawBlock("latex", "\\end{" .. env_name .. "}"))
  el.content:insert(pandoc.RawBlock("html", "</details>"))
  return el
end

return {
  { Meta = read_settings },
  { Div = hide },
}
