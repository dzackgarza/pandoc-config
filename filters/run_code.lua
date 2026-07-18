-- run_code.lua — execute fenced code blocks at build time and embed their output.
--
-- Follows the tikzcd.lua precedent: intercept a block, shell out to an external
-- interpreter, cache by content hash, and splice the result back into the AST.
--
-- Trigger (opt-in, to avoid running display-only code): a CodeBlock runs iff it
-- carries the class `run` (or `silent`) alongside exactly one registered
-- language class. Plain ```lean / ```python blocks are left untouched.
--
--   ```{.python .run}      -> runs, shows source + output
--   ```{.lean .run}        -> runs, shows source + output
--   ```{.python .silent}   -> runs for side effects, emits nothing
--
-- `sage` is deliberately NOT registered here: Sage cells are owned by the
-- dedicated sagemath-pandoc-filter (panflute, runs under `sage --python`).
--
-- Lean imports (Mathlib etc.) are resolved by Lake, not the toolchain, so Lean
-- cells run inside a prebuilt lake project via `lake env lean`. The default is
-- the research DSL-spike env below (mathlib + batteries + aesop + Paperproof,
-- already compiled); any build overrides it with RUN_CODE_LEAN_PROJECT, and a
-- local project's own lakefile naturally wins.
--
-- Env knobs (per language, <LANG> = PYTHON | LEAN | BASH | SH):
--   RUN_CODE_<LANG>          full interpreter-command override (escape hatch)
--   RUN_CODE_<LANG>_PROJECT  lake project dir; runs `lake env <cmd>` with that cwd
--   RUN_CODE_<LANG>_PREAMBLE text prepended to every cell before running (e.g.
--                            "import Mathlib") — off unless set; not shown in source
--   RUN_CODE_CACHE           cache dir (default $PANDOC_DIR/figures/run-code-cache)
--   RUN_CODE_STRICT=1        abort the build on any nonzero exit instead of
--                            rendering the error inline

local home = os.getenv("HOME")
local pandoc_dir = os.getenv("PANDOC_DIR") or (home .. "/.pandoc")
local cache_dir = os.getenv("RUN_CODE_CACHE") or (pandoc_dir .. "/figures/run-code-cache")
local strict = os.getenv("RUN_CODE_STRICT") == "1"

-- Chosen standard Lean env: the research DSL spike's prebuilt lake project.
-- Deliberate cross-repo coupling (user decision 2026-07-18); if the spike is
-- removed, set RUN_CODE_LEAN_PROJECT to another built mathlib project.
local DEFAULT_LEAN_PROJECT = home .. "/research/computations/experiments/lean_category_dsl_spike"

-- language registry: class -> { cmd = default interpreter, ext = temp-file extension }
local runners = {
  python = { cmd = "python3", ext = "py" },
  bash   = { cmd = "bash",    ext = "sh" },
  sh     = { cmd = "sh",      ext = "sh" },
  lean   = { cmd = "lean",    ext = "lean" },
}

local function getenv(name)
  local v = os.getenv(name)
  if v and v ~= "" then return v end
  return nil
end

-- resolve how a language runs: returns (command_string, cwd_or_nil).
-- RUN_CODE_<LANG> overrides the interpreter; a project dir switches to
-- `lake env <cmd>` run from that dir so imports resolve. Lean defaults to the
-- standard env above.
local function resolve(lang, spec)
  local U = lang:upper()
  local override = getenv("RUN_CODE_" .. U)
  local project = getenv("RUN_CODE_" .. U .. "_PROJECT")
  if lang == "lean" and project == nil and override == nil then
    project = DEFAULT_LEAN_PROJECT
  end
  local cmd = override or (project and ("lake env " .. spec.cmd)) or spec.cmd
  return cmd, project
end

-- pick the single registered language class on a block, or nil
local function lang_of(el)
  local found = nil
  for _, c in ipairs(el.classes) do
    if runners[c] then
      if found then return nil end  -- ambiguous: more than one language class
      found = c
    end
  end
  return found
end

local function read_file(path)
  local f = io.open(path, "r"); if not f then return nil end
  local s = f:read("*a"); f:close(); return s
end

local function write_file(path, s)
  local f = assert(io.open(path, "w")); f:write(s); f:close()
end

-- run `code` through `cmd` (optionally from `cwd`), capturing combined
-- stdout+stderr and the exit code. Returns (output_string, ok_boolean).
local function execute(cmd, cwd, code, ext)
  local out, ok
  pandoc.system.with_temporary_directory("run_code", function(dir)
    local src = dir .. "/cell." .. ext
    write_file(src, code)
    local full = (cwd and ("cd " .. cwd .. " && ") or "") .. cmd .. " " .. src .. " 2>&1"
    local h = assert(io.popen(full, "r"))
    out = h:read("*a") or ""
    local _, _, code_exit = h:close()
    ok = (code_exit == 0)
  end)
  return out, ok
end

function CodeBlock(el)
  local lang = lang_of(el)
  if not lang then return nil end
  local run    = el.classes:includes("run")
  local silent = el.classes:includes("silent")
  if not (run or silent) then return nil end

  local spec = runners[lang]
  local cmd, cwd = resolve(lang, spec)
  local preamble = getenv("RUN_CODE_" .. lang:upper() .. "_PREAMBLE")
  local run_src = preamble and (preamble .. "\n" .. el.text) or el.text

  -- cache key folds in everything that changes the result: command, env dir,
  -- preamble, and the (preamble-augmented) source.
  local key = pandoc.sha1(table.concat({ lang, cmd, cwd or "", preamble or "", run_src }, "\0"))
  local cache_path = cache_dir .. "/" .. key
  local cached = read_file(cache_path)

  local output, ok
  if cached then
    -- cache stores "<0|1>\n<output>": first line is the ok flag
    ok = cached:sub(1, 1) == "1"
    output = cached:sub(3)
  else
    os.execute("mkdir -p " .. cache_dir)
    output, ok = execute(cmd, cwd, run_src, spec.ext)
    write_file(cache_path, (ok and "1" or "0") .. "\n" .. output)
  end

  if not ok and strict then
    error("run_code: " .. lang .. " block failed (RUN_CODE_STRICT):\n" .. output)
  end

  if silent then return {} end

  -- keep the source block (display + highlighting, WITHOUT preamble), append output
  output = output:gsub("%s+$", "")
  local out_class = ok and "code-output" or "code-error"
  local blocks = { el }
  if #output > 0 then
    blocks[#blocks + 1] = pandoc.Div(
      { pandoc.CodeBlock(output) },
      pandoc.Attr("", { out_class }, {})
    )
  end
  return blocks
end
