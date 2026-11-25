function Str(elem)
  if not elem.text:match "unanswered_questions" then
    return elem
  end
  return pandoc.Str((elem.text:gsub("[()]?#unanswered_questions[)]?", "")))
end
