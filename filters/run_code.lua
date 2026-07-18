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
-- Each language maps to an argv-0 command + file extension. The command is
-- overridable via env (e.g. RUN_CODE_LEAN="lake env lean") because real Lean
-- setups need a lake project env for mathlib; a bare `lean` only elaborates
-- toolchain-free snippets.
--
-- Env knobs:
--   RUN_CODE_<LANG>   override the interpreter command for a language
--   RUN_CODE_CACHE    cache dir (default $PANDOC_DIR/figures/run-code-cache)
--   RUN_CODE_STRICT=1 abort the build on any nonzero exit instead of rendering
--                     the error inline

local home = os.getenv("HOME")
local pandoc_dir = os.getenv("PANDOC_DIR") or (home .. "/.pandoc")
local cache_dir = os.getenv("RUN_CODE_CACHE") or (pandoc_dir .. "/figures/run-code-cache")
local strict = os.getenv("RUN_CODE_STRICT") == "1"

-- language registry: class -> { cmd = default interpreter, ext = temp-file extension }
local runners = {
  python = { cmd = "python3", ext = "py" },
  bash   = { cmd = "bash",    ext = "sh" },
  sh     = { cmd = "sh",      ext = "sh" },
  lean   = { cmd = "lean",    ext = "lean" },
}

local function command_for(lang, spec)
  local override = os.getenv("RUN_CODE_" .. lang:upper())
  return (override and override ~= "") and override or spec.cmd
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

-- run `code` through the language's interpreter, capturing combined stdout+stderr
-- and the exit code. Returns (output_string, ok_boolean).
local function execute(lang, spec, code)
  local out, ok
  pandoc.system.with_temporary_directory("run_code", function(dir)
    local src = dir .. "/cell." .. spec.ext
    write_file(src, code)
    local cmd = command_for(lang, spec) .. " " .. src .. " 2>&1"
    local h = assert(io.popen(cmd, "r"))
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
  local key = pandoc.sha1(lang .. "\0" .. command_for(lang, spec) .. "\0" .. el.text)
  local cache_path = cache_dir .. "/" .. key
  local cached = read_file(cache_path)

  local output, ok
  if cached then
    -- cache stores "<0|1>\n<output>": first line is the ok flag
    ok = cached:sub(1, 1) == "1"
    output = cached:sub(3)
  else
    os.execute("mkdir -p " .. cache_dir)
    output, ok = execute(lang, spec, el.text)
    write_file(cache_path, (ok and "1" or "0") .. "\n" .. output)
  end

  if not ok and strict then
    error("run_code: " .. lang .. " block failed (RUN_CODE_STRICT):\n" .. output)
  end

  if silent then return {} end

  -- keep the source block (display + highlighting), append the captured output
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
