local notices = {
  { class = "solution", text = "Solution omitted." },
  { class = "proof", text = "Proof omitted." },
  { class = "strategy", text = "Strategy omitted." },
  { class = "concept", text = "Concept review omitted." },
}

if not (FORMAT:match "latex" or FORMAT:match "pdf") then
  return {}
end

local kill_proofs = false

local function read_settings(meta)
  kill_proofs = meta["kill_proofs"] ~= nil
end

local function omit(el)
  if not kill_proofs then
    return el
  end
  for _, notice in ipairs(notices) do
    if el.classes:includes(notice.class) then
      pandoc.log.info("hide_solutions_pdf: " .. notice.class .. " omitted")
      return pandoc.Para(pandoc.Emph { pandoc.Str(notice.text) })
    end
  end
  return el
end

return {
  { Meta = read_settings },
  { Div = omit },
}
