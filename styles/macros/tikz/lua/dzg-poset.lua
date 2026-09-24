-- Hasse diagrams of serialized posets: layout for \posetfromjson
-- (constructors/dzg-posets.tex).
--
-- Input: a poset as networkx node-link JSON, the Hasse diagram directed from
-- each element to the elements covering it (Sage:
--   networkx.node_link_data(G) for the DiGraph of P.cover_relations()):
--   { "nodes": [ { "id": <id>, "name": <TikZ name>, "label": <TeX>,
--                  "grade": <int or "p/q"> }, ... ],
--     "links": [ { "source": <x>, "target": <y> }, ... ] }   -- x < y a cover
-- ("edges" is accepted for "links", as networkx >= 3.4 writes it). "name",
-- "label" and "grade" are optional; the node is named by "name", else by
-- "id"; a grade is on every element or on none.
--
-- Layout:
-- 1. A height h with h(x) < h(y) for every cover x < y: the given grades, or
--    a grading computed from chain lengths (below).
-- 2. Graphviz dot (Gansner, Koutsofios, North and Vo, "A technique for
--    drawing directed graphs", 1993: median-heuristic crossing reduction and
--    network-simplex coordinates) orders and spaces each layer of equal
--    height: every element is a fixed box of the declared size, the elements
--    of one height share a rank, and a cover spans as many ranks as heights
--    lie between its ends.
-- 3. Each element is placed at x from dot and y = (h - max h) * grade distance,
--    so heights, rational ones included, are spaced exactly.
--
-- Computed gradings (`poset grading`). On a graded poset all four agree with
-- the rank up to a shift:
--   balanced (default)         h(x) = (b(x) - t(x)) / 2, where b(x) is the
--                              length of a longest chain from a minimal
--                              element to x and t(x) of one from x to a
--                              maximal element. Order duality reflects the
--                              drawing, so a self-dual poset (a Tamari
--                              lattice) is drawn symmetric, and short chains
--                              sit at mid height, not on the top or bottom
--                              row.
--   longest chain from bottom  h(x) = b(x). For a subgroup lattice of a
--                              solvable group this is the number of prime
--                              factors of |H|, the drawing by order.
--   longest chain to top       h(x) = -t(x).
--   minimum total cover length the ranks of dot's own layering (network
--                              simplex: every cover spans at least one layer
--                              and the total span is least); compact, and
--                              crowds the middle layers.
-- Shortest and mean chain lengths are not gradings: on Tamari lattices,
-- subgroup lattices and random posets they draw covers level or downward.
-- A grading that draws a cover level or downward is an error.

require("lualibs-util-jsn")

local poset = {}

local function parse_grade(text)
  local p, q = tostring(text):match("^%s*(%-?%d+)%s*/%s*(%d+)%s*$")
  if p then return tonumber(p) / tonumber(q) end
  return assert(tonumber(text), "dzg.poset: grade `" .. tostring(text) .. "' is not a rational")
end

-- Topological order from the maximal elements down.
local function top_down_order(ids, up, down)
  local indegree, order, queue = {}, {}, {}
  for _, id in ipairs(ids) do
    indegree[id] = #up[id]
    if indegree[id] == 0 then queue[#queue + 1] = id end
  end
  local head = 1
  while head <= #queue do
    local id = queue[head]; head = head + 1
    order[#order + 1] = id
    for _, lower in ipairs(down[id]) do
      indegree[lower] = indegree[lower] - 1
      if indegree[lower] == 0 then queue[#queue + 1] = lower end
    end
  end
  assert(#order == #ids, "dzg.poset: the cover relations contain a cycle")
  return order
end

-- The length of a longest chain along `step` from each element, visiting
-- `order` so that every element comes after the elements `step` reaches.
local function longest_chains(order, step)
  local longest = {}
  for _, id in ipairs(order) do
    local length = 0
    for _, other in ipairs(step[id]) do length = math.max(length, longest[other] + 1) end
    longest[id] = length
  end
  return longest
end

-- Runs dot on the covers; returns x and y (in cm) by element. With `layer`,
-- the elements of one layer share a rank and a cover spans as many ranks as
-- layers lie between its ends; without it dot assigns the ranks itself,
-- minimising the total number of ranks the covers span (network simplex).
local function run_dot(ids, covers, layer, width, height, sep)
  assert(io.popen, "dzg.poset: \\posetfromjson runs Graphviz dot; compile with --shell-escape")
  local lines = { "digraph P {",
    string.format("node [shape=box, fixedsize=true, width=%.4f, height=%.4f, label=\"\"];",
      width / 2.54, height / 2.54),
    string.format("nodesep=%.4f; ranksep=0.3; edge [arrowhead=none];", sep / 2.54) }
  if layer then
    local by_layer = {}
    for _, id in ipairs(ids) do
      by_layer[layer[id]] = by_layer[layer[id]] or {}
      table.insert(by_layer[layer[id]], id .. ";")
    end
    for _, members in pairs(by_layer) do
      lines[#lines + 1] = "{rank=same; " .. table.concat(members, " ") .. "}"
    end
  end
  for _, c in ipairs(covers) do
    local span = layer and (layer[c[1]] - layer[c[2]]) or 1
    lines[#lines + 1] = string.format("%s -> %s [minlen=%d];", c[2], c[1], span)
  end
  for _, id in ipairs(ids) do lines[#lines + 1] = id .. ";" end
  lines[#lines + 1] = "}"
  local input = os.tmpname()
  local handle = assert(io.open(input, "w"))
  handle:write(table.concat(lines, "\n"))
  handle:close()
  local pipe = assert(io.popen("dot -Tplain " .. input, "r"))
  local x, y = {}, {}
  for line in pipe:lines() do
    local name, px, py = line:match("^node%s+(%S+)%s+(%S+)%s+(%S+)")
    if name then x[name], y[name] = tonumber(px) * 2.54, tonumber(py) * 2.54 end
  end
  pipe:close()
  os.remove(input)
  for _, id in ipairs(ids) do
    assert(x[id], "dzg.poset: dot placed no element " .. id)
  end
  return x, y
end

local function heights(ids, up, down, given, method, covers, width, height, sep)
  if next(given) then
    for _, id in ipairs(ids) do
      assert(given[id], "dzg.poset: element " .. id .. " has no grade")
    end
    return given
  end
  local h = {}
  if method == "minimum total cover length" then
    local _, y = run_dot(ids, covers, nil, width, height, sep)
    local levels = {}
    for _, id in ipairs(ids) do levels[#levels + 1] = y[id] end
    table.sort(levels)
    local index, count = {}, 0
    for i, v in ipairs(levels) do
      if i == 1 or v - levels[i - 1] > 1e-6 then count = count + 1 end
      index[v] = count
    end
    for _, id in ipairs(ids) do h[id] = index[y[id]] end
    return h
  end
  local order = top_down_order(ids, up, down)
  local reverse = {}
  for i = #order, 1, -1 do reverse[#reverse + 1] = order[i] end
  local to_top = longest_chains(order, up)
  local from_bottom = longest_chains(reverse, down)
  for _, id in ipairs(ids) do
    if method == "longest chain to top" then h[id] = -to_top[id]
    elseif method == "longest chain from bottom" then h[id] = from_bottom[id]
    elseif method == "balanced" then h[id] = (from_bottom[id] - to_top[id]) / 2
    else error("dzg.poset: unknown poset grading `" .. tostring(method) .. "'") end
  end
  return h
end

-- \posetfromjson: `options` are the figure's TikZ keys for the scope,
-- `method` the grading, the lengths in cm. Elements are keyed n1, n2, ...
-- internally (dot needs no quoting); the TikZ node of an element is named by
-- its "name", else its "id", which must then be a TikZ node name.
function poset.emit(path, options, method, width, height, sep, distance)
  local file = kpse.find_file(path) or path
  local handle = assert(io.open(file, "r"), "dzg.poset: cannot open " .. path)
  local data = utilities.json.tolua(handle:read("*a"))
  handle:close()
  local links = data.links or data.edges
  assert(data.nodes and links, "dzg.poset: " .. path .. " is not node-link JSON")

  local keys, key_of, names, labels, given, up, down, covers = {}, {}, {}, {}, {}, {}, {}, {}
  for k, node in ipairs(data.nodes) do
    local key = "n" .. k
    key_of[tostring(node.id)] = key
    keys[#keys + 1], labels[key], up[key], down[key] = key, node.label or "", {}, {}
    names[key] = tostring(node.name or node.id)
    assert(names[key]:match("^[%w_%-]+$"), "dzg.poset: `" .. names[key]
      .. "' is not a TikZ node name; give the element a \"name\"")
    if node.grade ~= nil then given[key] = parse_grade(node.grade) end
  end
  for _, link in ipairs(links) do
    local lower = assert(key_of[tostring(link.source)], "dzg.poset: no element " .. tostring(link.source))
    local upper = assert(key_of[tostring(link.target)], "dzg.poset: no element " .. tostring(link.target))
    covers[#covers + 1] = { lower, upper }
    table.insert(up[lower], upper)
    table.insert(down[upper], lower)
  end

  local h = heights(keys, up, down, given, method, covers, width, height, sep)
  local bad = 0
  for _, c in ipairs(covers) do
    if h[c[2]] <= h[c[1]] then bad = bad + 1 end
  end
  assert(bad == 0, "dzg.poset: the grading `" .. method .. "' draws " .. bad
    .. " cover(s) of " .. path .. " level or downward")

  local values = {}
  for _, key in ipairs(keys) do values[#values + 1] = h[key] end
  table.sort(values, function(a, b) return a > b end)
  local layer_of, count = {}, 0
  for i, v in ipairs(values) do
    if i == 1 or values[i - 1] - v > 1e-9 then count = count + 1 end
    layer_of[v] = count
  end
  local layer = {}
  for _, key in ipairs(keys) do layer[key] = layer_of[h[key]] end

  local x = run_dot(keys, covers, layer, width, height, sep)
  local top = values[1]
  local out, list = { "\\begin{scope}[" .. options .. "]" }, {}
  for _, key in ipairs(keys) do
    list[#list + 1] = names[key]
    out[#out + 1] = string.format("\\node[poset element] (%s) at (%.4fcm,%.4fcm) {%s};",
      names[key], x[key], (h[key] - top) * distance, labels[key])
  end
  out[#out + 1] = "\\begin{scope}[on edge layer]"
  for _, c in ipairs(covers) do
    out[#out + 1] = string.format("\\draw[poset cover] (%s) -- (%s);", names[c[2]], names[c[1]])
  end
  out[#out + 1] = "\\end{scope}\\end{scope}"
  tex.sprint("\\gdef\\posetelements{" .. table.concat(list, ",") .. "}")
  tex.sprint(table.concat(out, " "))
end

return poset
