--[==[
wikilinks.lua — turns each `[[target#heading|label]]` wikilink into an
internal link to the heading its editor resolved it to.

The editor (Zettlr) is the only resolver of wikilinks. It writes a JSON file
and names it in the environment variable PANDOC_WIKILINKS:

  {
    "inputs": [ { "headings": 3 }, { "headings": 5 } ],
    "links": { "chain#Second step": { "input": 1, "heading": 1 } }
  }

`inputs` lists, in the order pandoc reads them, how many headings each input
file has. `links` maps the raw target of a wikilink (the text before `|`) to
the input it names and the 0-based index of the target heading in that
input. A wikilink whose target is not in `links` (a missing or ambiguous
document, or one outside this export) becomes its label.

The reader extension `wikilinks_title_after_pipe` makes the wikilinks. The
filter must run before any filter that adds headings, such as include.lua.
]==]

local function load_map()
  local file_name = os.getenv('PANDOC_WIKILINKS')
  if file_name == nil or file_name == '' then
    return { inputs = {}, links = {} }
  end
  local handle = io.open(file_name, 'r')
  if handle == nil then
    error('wikilinks.lua: cannot read PANDOC_WIKILINKS file ' .. file_name)
  end
  local text = handle:read('a')
  handle:close()
  return pandoc.json.decode(text, false)
end

function Pandoc(doc)
  local map = load_map()

  local identifiers = {}
  doc:walk({
    Header = function(header)
      table.insert(identifiers, header.identifier)
    end
  })

  local first_heading = {}
  local expected = 0
  for index, input in ipairs(map.inputs) do
    first_heading[index - 1] = expected
    expected = expected + input.headings
  end
  if next(map.links) ~= nil and expected ~= #identifiers then
    error(string.format(
      'wikilinks.lua: the editor counted %d headings in the inputs, pandoc read %d',
      expected, #identifiers))
  end

  return doc:walk({
    Link = function(link)
      if not link.classes:includes('wikilink') then
        return nil
      end
      local target = map.links[link.target]
      if target == nil then
        return link.content
      end
      local identifier = identifiers[first_heading[target.input] + target.heading + 1]
      if identifier == nil or identifier == '' then
        error('wikilinks.lua: the heading of [[' .. link.target .. ']] has no identifier')
      end
      link.target = '#' .. identifier
      return link
    end
  })
end
