-- lamport_proof.lua
--
-- This filter gives Markdown a small, structured surface syntax for
-- Lamport-style proofs. Pandoc's fenced_divs reader parses the source into
-- native Div nodes; this file validates that tree, assigns hierarchical step
-- numbers, resolves pf-ref links, and selects a writer-specific rendering.
--
-- The .pf-* class prefix is intentional. The repository already uses .proof
-- for amsthm environments, while pf2.sty also defines a proof environment.
-- Keeping this namespace separate lets the semantic pass run beside those
-- existing filters without changing their meaning.
--
-- Surface syntax:
--   ::: {.pf}
--   ::: {.pf-step #label} statement :::
--   :::: {.pf-proof} nested steps or proof prose ::::
--   :::
-- Step IDs are Lamport labels. A Markdown link such as
-- [step](#label){.pf-ref} becomes the assigned hierarchical step number.
-- The LaTeX branch emits pf2.sty commands; the consuming template must load a
-- compatible Lamport-proof implementation because the commands are not part
-- of standard LaTeX.

local clause_classes = {
  ["pf-assume"] = "assume",
  ["pf-prove"] = "prove",
  ["pf-case"] = "case",
  ["pf-suffices"] = "suffices",
  ["pf-define"] = "define",
  ["pf-let"] = "let",
}

local special_step_classes = {
  ["pf-case"] = "Case",
  ["pf-suffices"] = "Suffices",
  ["pf-define"] = "Define",
  ["pf-let"] = "Let",
}

local labels = {}

local function has_class(element, class)
  for _, candidate in ipairs(element.classes or {}) do
    if candidate == class then
      return true
    end
  end
  return false
end

local function is_step(element)
  return element.t == "Div" and (
    has_class(element, "pf-step")
    or has_class(element, "pf-qed")
  )
end

local function is_proof(element)
  return element.t == "Div" and has_class(element, "pf-proof")
end

local function is_clause(element)
  if element.t ~= "Div" then
    return false
  end
  for class in pairs(clause_classes) do
    if has_class(element, class) then
      return true
    end
  end
  return has_class(element, "pf-conj") or has_class(element, "pf-disj")
end

local function proof_error(message)
  error("lamport proof: " .. message, 0)
end

local function valid_label(label)
  return label ~= "" and label:match("^[A-Za-z][A-Za-z0-9:_%-%.]*$") ~= nil
end

local function join_path(path, index)
  local parts = {}
  for _, value in ipairs(path) do
    parts[#parts + 1] = tostring(value)
  end
  parts[#parts + 1] = tostring(index)
  return table.concat(parts, ".")
end

local function set_number(element, number, level)
  element.attributes["data-pf-number"] = number
  element.attributes["data-pf-level"] = tostring(level)
end

local function special_step_kind(element)
  local selected
  for class in pairs(special_step_classes) do
    if has_class(element, class) then
      if selected ~= nil then
        proof_error("a step can have only one special kind")
      end
      selected = class
    end
  end
  return selected
end

-- Assign numbers and enforce the proof grammar before any writer-specific
-- transformation. A proof container numbers only its direct step children;
-- nested proof containers receive the parent step path as their prefix.
local function annotate_container(container, parent_path, is_root)
  local level = #parent_path + 1
  container.attributes["data-pf-level"] = tostring(level)
  local step_index = 0

  for _, child in ipairs(container.content) do
    if is_step(child) then
      step_index = step_index + 1
      local number = join_path(parent_path, step_index)
      set_number(child, number, level)

      if has_class(child, "pf-step") then
        local label = child.identifier
        if not valid_label(label) then
          proof_error("every pf-step needs a label-safe identifier")
        end
        if labels[label] ~= nil then
          proof_error("duplicate step label: " .. label)
        end
        labels[label] = { number = number, element = child }
        special_step_kind(child)
      elseif child.identifier ~= "" then
        proof_error("pf-qed steps cannot have identifiers")
      end

      local nested_proof
      for _, part in ipairs(child.content) do
        if is_proof(part) then
          if nested_proof ~= nil then
            proof_error("a step can have only one pf-proof body")
          end
          nested_proof = part
        elseif part.t == "Div" and not is_clause(part) then
          proof_error("unknown div inside a proof step")
        end
      end
      if nested_proof ~= nil then
        annotate_container(nested_proof, (function()
          local path = {}
          for _, value in ipairs(parent_path) do
            path[#path + 1] = value
          end
          path[#path + 1] = step_index
          return path
        end)(), false)
      end
    elseif child.t == "Div" then
      if is_root then
        proof_error("the pf root can contain only steps")
      end
      proof_error("a pf-proof can contain only steps and proof prose")
    elseif is_root then
      proof_error("the pf root can contain only steps")
    end
  end

  if is_root and step_index == 0 then
    proof_error("the pf root must contain at least one step")
  end
end

local function collect_roots(blocks, roots)
  for _, block in ipairs(blocks) do
    if block.t == "Div" then
      if has_class(block, "pf") then
        roots[#roots + 1] = block
      else
        collect_roots(block.content, roots)
      end
    elseif block.t == "BlockQuote" then
      collect_roots(block.content, roots)
    elseif block.t == "BulletList" or block.t == "OrderedList" then
      for _, item in ipairs(block.content) do
        collect_roots(item, roots)
      end
    end
  end
end

local function is_latex_output()
  return FORMAT:match("latex") ~= nil or FORMAT == "pdf" or FORMAT == "beamer"
end

local function is_markdown_output()
  return FORMAT:match("markdown") ~= nil
end

local function reference_label(link)
  local target = link.target
  if type(target) ~= "string" or not target:match("^#") then
    proof_error("pf-ref links must target a step ID")
  end
  return target:sub(2)
end

local function resolve_reference(link)
  if not has_class(link, "pf-ref") then
    return link
  end
  local label = reference_label(link)
  local entry = labels[label]
  if entry == nil then
    proof_error("reference to unknown step label: " .. label)
  end
  if is_latex_output() then
    return pandoc.RawInline("latex", "\\pfref{" .. label .. "}")
  end
  link.content = pandoc.Inlines({ pandoc.Str(entry.number) })
  return link
end

local function render_blocks(blocks)
  return pandoc.write(pandoc.Pandoc(blocks), "latex")
end

local function append(output, value)
  output[#output + 1] = value
end

local function render_clause(clause)
  local command
  for class, candidate in pairs(clause_classes) do
    if has_class(clause, class) then
      command = candidate
      break
    end
  end
  if command == nil then
    return render_blocks(clause.content)
  end
  return "\\" .. command .. "\\bgroup\n" .. render_blocks(clause.content) .. "\\egroup\n"
end

local render_step

local function render_proof_body(proof)
  local steps = {}
  local prose = {}
  for _, block in ipairs(proof.content) do
    if is_step(block) then
      steps[#steps + 1] = block
    else
      prose[#prose + 1] = block
    end
  end

  local output = {}
  if #prose > 0 then
    append(output, "\\pf\\ " .. render_blocks(prose) .. "~\\qed")
  end
  if #steps > 0 then
    append(output, "\\begin{proof}")
    for _, step in ipairs(steps) do
      append(output, render_step(step))
    end
    append(output, "\\end{proof}")
  end
  return table.concat(output, "\n")
end

render_step = function(step)
  local body = {}
  local statement = {}
  local nested_proof

  for _, block in ipairs(step.content) do
    if is_proof(block) then
      nested_proof = block
    elseif not is_clause(block) then
      statement[#statement + 1] = block
    end
  end

  local kind = special_step_kind(step)
  if kind ~= nil then
    append(body, "\\textsc{" .. special_step_classes[kind] .. ":}\\ ")
  end
  if #statement > 0 then
    append(body, render_blocks(statement))
  end
  -- Emit clauses after the statement, matching Lamport's Assume/Prove order.
  for _, block in ipairs(step.content) do
    if is_clause(block) then
      append(body, render_clause(block))
    end
  end
  if nested_proof ~= nil then
    append(body, render_proof_body(nested_proof))
  end

  if has_class(step, "pf-qed") then
    local output = { "\\qedstep" }
    if #body > 0 then
      append(output, "\\pf\\ " .. table.concat(body, "\n") .. "~\\qed")
    end
    return table.concat(output, "\n")
  end

  return "\\begin{step+}{" .. step.identifier .. "}\n"
    .. table.concat(body, "\n")
    .. "\n\\end{step+}"
end

local function render_root(root)
  local opening = root.attributes["numbering"] == "long"
    and "\\pflongnumbers"
    or "\\pfshortnumbers"
  local output = { opening, "\\begin{proof}" }
  for _, step in ipairs(root.content) do
    append(output, render_step(step))
  end
  append(output, "\\end{proof}")
  return pandoc.RawBlock("latex", table.concat(output, "\n"))
end

local function add_html_number(step)
  local text = step.attributes["data-pf-number"]
  if text == nil then
    proof_error("internal numbering invariant failed")
  end
  local label = text .. "."
  if has_class(step, "pf-qed") then
    label = label .. " QED"
  end
  local number = pandoc.Span({ pandoc.Str(label) }, { class = "pf-number" })
  local first = step.content[1]
  if first ~= nil and (first.t == "Para" or first.t == "Plain") then
    table.insert(first.content, 1, pandoc.Space())
    table.insert(first.content, 1, number)
  else
    table.insert(step.content, 1, pandoc.Para({ number }))
  end
end

local function add_html_numbers(container)
  for _, block in ipairs(container.content) do
    if is_step(block) then
      add_html_number(block)
      for _, child in ipairs(block.content) do
        if is_proof(child) then
          add_html_numbers(child)
        end
      end
    end
  end
end

local function clear_annotations(container)
  container.attributes["data-pf-numbering"] = nil
  container.attributes["data-pf-level"] = nil
  container.attributes["data-pf-number"] = nil
  for _, block in ipairs(container.content) do
    if block.t == "Div" then
      clear_annotations(block)
    end
  end
end

local function transform_blocks(blocks)
  local result = {}
  for _, block in ipairs(blocks) do
    if has_class(block, "pf") and is_latex_output() then
      result[#result + 1] = render_root(block)
    else
      if block.t == "Div" then
        block.content = transform_blocks(block.content)
      elseif block.t == "BlockQuote" then
        block.content = transform_blocks(block.content)
      elseif block.t == "BulletList" or block.t == "OrderedList" then
        for index, item in ipairs(block.content) do
          block.content[index] = transform_blocks(item)
        end
      end
      result[#result + 1] = block
    end
  end
  return result
end

function Pandoc(document)
  labels = {}
  local roots = {}
  collect_roots(document.blocks, roots)
  for _, root in ipairs(roots) do
    local numbering = root.attributes["numbering"] or "short"
    if numbering ~= "short" and numbering ~= "long" then
      proof_error("numbering must be short or long")
    end
    root.attributes["data-pf-numbering"] = numbering
    annotate_container(root, {}, true)
  end

  if is_markdown_output() then
    for _, root in ipairs(roots) do
      clear_annotations(root)
    end
    return document
  end

  if not is_latex_output() then
    -- Add number spans before walking references. Pandoc walks return a new
    -- document value, so modifying roots collected from the old value later
    -- would not affect the document sent to the writer.
    for _, root in ipairs(roots) do
      add_html_numbers(root)
    end
  end
  document = document:walk({ Link = resolve_reference })
  if is_latex_output() then
    document.blocks = transform_blocks(document.blocks)
  end
  return document
end
