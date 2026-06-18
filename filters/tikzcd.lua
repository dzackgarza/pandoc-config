local system = require 'pandoc.system'
local home = os.getenv("HOME")
package.path = package.path .. ';' .. home .. '/.pandoc/filters/?.lua;'
require "utilities"

-- Logging helper: writes to stderr, no-op unless TIKZCD_DEBUG=1
local debug_mode = os.getenv("TIKZCD_DEBUG") == "1"
local function log(msg)
  if debug_mode then
    io.stderr:write("[tikzcd] " .. msg .. "\n")
  end
end

-- Output directories
local pandoc_dir = os.getenv("PANDOC_DIR") or (home .. "/dotfiles/pandoc")
local figures_dir = os.getenv("FIGURES_DIR") or (home .. "/.pandoc/figures")
local svg_dir = os.getenv("SVG_DIR") or (figures_dir .. "/rendered")

-- Per-figure preamble template (Phase D / D-3 / P92): the config-declared
-- standalone LaTeX document each figure body is wrapped in, supplied by the app
-- from [figures].template (render.sh exports it as FIGURE_TEMPLATE_FILE). It
-- carries the QTikz `.pgs` `<>` `TemplateReplaceText` marker where the figure
-- source is substituted, plus `$tikzdefs$`/`$tikzstyles$` markers the shared
-- palette paths fill (P91). Required, config-validated ExistingFile — no default,
-- no fallback to a baked-in template: a missing var when a figure is ACTUALLY
-- compiled means the renderer wiring is broken, so fail loud. Read LAZILY at
-- compile time (not at filter load) so the doctor's empty-stdin invocation probe,
-- which loads the filter but compiles no figure, needs no render-context env.
-- Returns (compiled_template, raw_template_string): the raw string is folded into
-- the figure cache key so swapping the template content changes the render.
local function figure_template()
  local template_path = os.getenv("FIGURE_TEMPLATE_FILE")
  if not template_path or template_path == "" then
    error("tikzcd.lua: FIGURE_TEMPLATE_FILE is not set (the config-declared per-figure template)")
  end
  local template_file = io.open(template_path, "r")
  if not template_file then
    error("tikzcd.lua: per-figure template not found at " .. template_path)
  end
  local template_str = template_file:read("*a")
  template_file:close()
  return pandoc.template.compile(template_str), template_str
end

-- Shared figure palette (Phase D / D-2 / P91): the absolute paths of the ONE
-- shared .tikzstyles and .tikzdefs every figure \input's, supplied by the app
-- from the config-declared [figures].tikzstyles / [figures].tikzdefs (render.sh
-- exports them as TIKZSTYLES_FILE / TIKZDEFS_FILE). Both are required,
-- config-validated ExistingFiles — no default, no fallback: a missing var when a
-- figure is ACTUALLY compiled means the renderer wiring is broken, so fail loud
-- rather than compile a figure that silently ignores the shared palette. Read
-- LAZILY at compile time (not at filter load) so the doctor's empty-stdin
-- invocation probe, which loads the filter but compiles no figure, does not
-- require the render-context env.
local function shared_palette()
  local tikzstyles_file = os.getenv("TIKZSTYLES_FILE")
  if not tikzstyles_file or tikzstyles_file == "" then
    error("tikzcd.lua: TIKZSTYLES_FILE is not set (the config-declared shared .tikzstyles)")
  end
  local tikzdefs_file = os.getenv("TIKZDEFS_FILE")
  if not tikzdefs_file or tikzdefs_file == "" then
    error("tikzcd.lua: TIKZDEFS_FILE is not set (the config-declared shared .tikzdefs)")
  end
  return tikzstyles_file, tikzdefs_file
end

-- Shared compilation core: given full LaTeX source, compile to PDF then SVG.
-- Returns (svg_path, pdf_path) or (nil, nil) on failure.
local function run_pdflatex_and_convert(tex_source, tmp_prefix, hash, doc_dir)
  local svg_path = svg_dir .. "/dzgtikz-" .. hash .. ".svg"
  local pdf_path = svg_dir .. "/dzgtikz-" .. hash .. ".pdf"

  local sf = io.open(svg_path, "r")
  if sf then sf:close() end
  local pf = io.open(pdf_path, "r")
  if pf then pf:close() end
  if sf and pf then
    return svg_path, pdf_path
  end

  os.execute("mkdir -p " .. svg_dir)

  local tmp = "/tmp/" .. tmp_prefix .. "-" .. hash
  os.execute("mkdir -p " .. tmp)
  local tex_path = tmp .. "/tikz.tex"

  local f = io.open(tex_path, "w")
  f:write(tex_source)
  f:close()

  local inputs_env = ""
  local styles_dir = pandoc_dir .. "/styles//"
  if doc_dir and doc_dir ~= "" then
    inputs_env = "TEXINPUTS=" .. doc_dir .. ":" .. styles_dir .. ":: "
  else
    inputs_env = "TEXINPUTS=" .. styles_dir .. ":: "
  end

  local cmd1 = inputs_env .. "pdflatex -interaction=nonstopmode -output-directory=" .. tmp .. " " .. tex_path .. " 2>&1"
  local ok1 = os.execute(cmd1)
  if not ok1 then
    os.execute("rm -rf " .. tmp)
    return nil, nil
  end

  local tmp_pdf = tmp .. "/tikz.pdf"
  os.execute("cp " .. tmp_pdf .. " " .. pdf_path)
  local ok2 = os.execute("pdf2svg " .. tmp_pdf .. " " .. svg_path .. " >/dev/null 2>&1")
  os.execute("rm -rf " .. tmp)

  if not ok2 then
    return nil, pdf_path
  end

  return svg_path, pdf_path
end

local function resolve_inputs(text, base_dir, depth)
  if not depth then depth = 1 end
  if depth > 10 then
    log("resolve_inputs: max depth exceeded, potential circular input")
    return text
  end

  local count
  repeat
    count = 0
    text = text:gsub("\\input%s-{(.-)}", function(filename)
      count = count + 1
      local full_path = filename
      local is_absolute = filename:sub(1,1) == "/" or filename:match("^%a+:")
      if not is_absolute then
        full_path = base_dir .. "/" .. filename
      end

      local file = io.open(full_path, "r")
      if not file then
        -- If it doesn't end with .tikz or .tex, try appending extensions
        if not filename:match("%.%a+$") then
          file = io.open(full_path .. ".tikz", "r")
          if not file then
            file = io.open(full_path .. ".tex", "r")
          end
        end
      end

      if file then
        local content = file:read("*a")
        file:close()
        -- Recursively resolve inputs inside the loaded content
        return resolve_inputs(content, base_dir, depth + 1)
      else
        log("resolve_inputs: WARNING: could not open input file " .. filename)
        return "\\input{" .. filename .. "}"
      end
    end)
  until count == 0

  return text
end

-- Compile a tikz snippet (e.g. \begin{tikzcd}...) by wrapping it in the
-- config-declared per-figure template (Phase D / D-3 / P92) at its `<>` marker.
-- Returns (svg_path, pdf_path) or (nil, nil) on failure.
local function compile_tikz(source)
  local doc_path = os.getenv("PANDOC_DOC_PATH")
  local doc_dir = "."
  if doc_path and doc_path ~= "" then
    doc_dir = doc_path:match("(.+)[/\\]") or doc_dir
  end

  local resolved_source = resolve_inputs(source, doc_dir)

  -- The shared palette paths fill the template's $tikzdefs$/$tikzstyles$ \input
  -- lines, so this figure compiles WITH the config-declared shared .tikzdefs +
  -- .tikzstyles in scope (Phase D / D-2 / P91).
  local tikzstyles_file, tikzdefs_file = shared_palette()

  -- The config-declared per-figure preamble template (Phase D / D-3 / P92): the
  -- standalone document this figure body is wrapped in. Read lazily here.
  local tikz_doc_template, template_str = figure_template()

  -- The cache key (hash) MUST fold in the shared palette CONTENT and the TEMPLATE
  -- content, not just the figure body: the same body compiled against a different
  -- shared .tikzstyles (P91's discriminator) or a different per-figure template
  -- (P92's discriminator swaps the template on disk) is a different figure.
  -- Hashing only the body would return a stale cached SVG when either changes, so
  -- read the shared files and include their bytes — and the template's bytes — in
  -- the hash. All are required ExistingFiles (config-validated), so a read failure
  -- is a broken environment.
  local function read_required(path, label)
    local fh = io.open(path, "r")
    if not fh then
      error("tikzcd.lua: cannot read " .. label .. " at " .. path)
    end
    local content = fh:read("*a")
    fh:close()
    return content
  end
  local styles_content = read_required(tikzstyles_file, "shared .tikzstyles")
  local defs_content = read_required(tikzdefs_file, "shared .tikzdefs")
  local hash = pandoc.sha1(
    resolved_source .. "\0" .. defs_content .. "\0" .. styles_content .. "\0" .. template_str
  )

  -- Fill the template's $tikzdefs$/$tikzstyles$ palette markers first (pandoc
  -- template), then substitute the figure source at the QTikz `<>` marker. The
  -- `<>` is plain text to pandoc's template engine (not a $...$ variable), so it
  -- survives the render untouched; substituting it AFTER keeps the figure source
  -- (which may contain `$` math) out of the pandoc-template pass entirely. A
  -- function replacement avoids gsub treating `%`/`\` in the source as special.
  local ctx = { tikzstyles = tikzstyles_file, tikzdefs = tikzdefs_file }
  local rendered = pandoc.layout.render(pandoc.template.apply(tikz_doc_template, ctx))
  if not rendered:find("<>", 1, true) then
    error("tikzcd.lua: per-figure template carries no `<>` source marker (QTikz convention)")
  end
  local tex_source = rendered:gsub("<>", function() return resolved_source end)

  log("compile_tikz: hash=" .. hash .. " source_length=" .. #resolved_source)
  if debug_mode then
    local preview = resolved_source:sub(1, 200):gsub("\n", "\\n")
    log("compile_tikz: source_preview: " .. preview)
  end
  return run_pdflatex_and_convert(tex_source, "tikzcd", hash, doc_dir)
end

-- Compile a full tikz document (from ```tikz code block) directly, no template.
-- Returns (svg_path, pdf_path) or (nil, nil) on failure.
local function compile_tikz_document(source)
  local doc_path = os.getenv("PANDOC_DOC_PATH")
  local doc_dir = "."
  if doc_path and doc_path ~= "" then
    doc_dir = doc_path:match("(.+)[/\\]") or doc_dir
  end

  local resolved_source = resolve_inputs(source, doc_dir)
  local hash = pandoc.sha1(resolved_source)
  return run_pdflatex_and_convert(resolved_source, "tikzfull", hash, doc_dir)
end

-- Shared helpers for building output from a compiled SVG/PDF pair.
local function make_latex_output(pdf_path, is_tikzcd)
  local base = pdf_path:gsub("%.pdf$", "")
  if is_tikzcd then
    return "\\begin{figure}[H]\n\\centering\n\\includesvg[width=\\columnwidth]{" .. base .. "}\n\\end{figure}"
  else
    return "\\begin{figure}\n\\centering\n\\includesvg[width=\\columnwidth]{" .. base .. "}\n\\end{figure}"
  end
end

local function namespace_svg_ids(svg_tag, prefix)
  -- Prefix all id="..." and xlink:href="#..." to prevent cross-SVG ID collisions
  -- when multiple inline SVGs share one HTML document.
  local result = svg_tag:gsub('id="([^"]*)"', 'id="' .. prefix .. '-%1"')
  result = result:gsub('xlink:href="#([^"]*)"', 'xlink:href="#' .. prefix .. '-%1"')
  return result
end

local function make_html_output(svg_path, css_class)
  local f = io.open(svg_path, "r")
  assert(f, "tikzcd.lua: SVG file missing after compilation: " .. svg_path)
  local svg_content = f:read("*a")
  f:close()

  local svg_tag = svg_content:match("<svg[^>]*>.-</svg>")
  if not svg_tag then
    svg_tag = svg_content
  end

  -- Namespace IDs using a short hash to prevent cross-SVG collisions
  local hash = pandoc.sha1(svg_tag):sub(1, 8)
  svg_tag = namespace_svg_ids(svg_tag, hash)

  local html = '<div style="text-align:center;">'
    .. '<span class="' .. css_class .. ' pandoc-preview-editable" data-edit-kind="' .. css_class .. '">'
    .. svg_tag
    .. '</span>'
    .. '</div>'
  return pandoc.Para(pandoc.RawInline('html', html))
end

if FORMAT:match 'latex' or FORMAT:match 'pdf' or FORMAT:match 'markdown' then
  function RawBlock(el)
    local is_tikzcd = starts_with('\\begin{tikzcd}', el.text)
    local is_tikzpic = starts_with('\\begin{tikzpicture}', el.text)
    if not is_tikzcd and not is_tikzpic then
      return el
    end

    log("RawBlock: processing " .. (is_tikzcd and "tikzcd" or "tikzpicture") .. " block, length=" .. #el.text)
    local _, pdf_path = compile_tikz(el.text)
    if not pdf_path then
      log("RawBlock: compilation FAILED for block")
      assert(pdf_path, "tikzcd.lua: compilation failed for tikz block")
    end
    log("RawBlock: compiled to " .. pdf_path)

    el.text = make_latex_output(pdf_path, is_tikzcd)
    return el
  end

  function CodeBlock(el)
    if not el.classes:includes("tikz") then
      return el
    end

    local _, pdf_path = compile_tikz_document(el.text)
    assert(pdf_path, "tikzcd.lua: compilation failed for tikz code block")

    return pandoc.RawBlock('latex', make_latex_output(pdf_path, false))
  end
end

if FORMAT:match 'html' then
  function RawBlock(el)
    local is_tikzcd = starts_with('\\begin{tikzcd}', el.text)
    local is_tikzpic = starts_with('\\begin{tikzpicture}', el.text)
    local is_pdftex = el.text:match("\\input%s-{(.-%.pdf_tex)}")
    if not is_tikzcd and not is_tikzpic and not is_pdftex then
      return el
    end

    log("RawBlock (html): processing tikz/pdftex block, length=" .. #el.text)
    local svg_path, _ = compile_tikz(el.text)
    if not svg_path then
      -- A figure that does NOT compile under the active per-figure template
      -- (Phase D / D-3 / P92: e.g. it requires a \usetikzlibrary the configured
      -- template omits) is ABSENT from the preview — it produces no <svg> — while
      -- the rest of the document still renders. The failure is loud in the filter
      -- log (and the figure visibly does not appear); dropping the single block,
      -- not aborting the whole render, is what makes a template swap observable in
      -- the live preview. Return the raw latex block unchanged: pandoc's HTML
      -- writer omits non-HTML raw blocks, so the failed figure leaves no element.
      io.stderr:write("[tikzcd] figure did not compile under the active per-figure template; omitting it from the preview\n")
      return el
    end
    log("RawBlock (html): compiled to " .. svg_path)

    local css_class = "tikzcd"
    if is_pdftex then
      css_class = "pdftex"
    elseif not is_tikzcd then
      css_class = "tikzpic"
    end

    return make_html_output(svg_path, css_class)
  end

  function CodeBlock(el)
    if not el.classes:includes("tikz") then
      return el
    end

    log("CodeBlock (html): processing tikz code block, length=" .. #el.text)
    local svg_path, _ = compile_tikz_document(el.text)
    if not svg_path then
      log("CodeBlock (html): compilation FAILED")
      assert(svg_path, "tikzcd.lua: compilation failed for tikz code block")
    end
    log("CodeBlock (html): compiled to " .. svg_path)

    return make_html_output(svg_path, "tikzcode")
  end
end
