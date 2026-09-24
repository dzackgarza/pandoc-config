# The compactifications of F_T over the Baily-Borel compactification, as two
# posets; writes semitoroidal.json and toroidal.json for \posetfromjson
# (figures/tikz/compactification_posets_over_BB.tex). In each, x < y when the
# compactification y is more degenerate than x, the order of the figure's
# arrows.
#   semitoroidal, strictly non-toroidal: the fans F^1, ..., F^4, the joins
#     F^{1,2}, F^{2,3}, F^{3,4} of neighbours, and the semitoroidal
#     compactification at the top.
#   toroidal: the fans Sigma^1, Sigma_Cox (the Coxeter fan, highlighted),
#     Sigma^3, the joins Sigma^{1,2}, Sigma^{2,3}, and the toroidal
#     compactification at the top.
#
#   sage compactifications-over-BB.sage
load("~/.pandoc/bin/poset_json.sage")


def chain_of_joins(names, top):
    joins = ["%s%s" % (a, b) for a, b in zip(names, names[1:])]
    covers = [(a, j) for j, a in zip(joins, names)] + [(b, j) for j, b in zip(joins, names[1:])]
    covers += [(j, top) for j in joins]
    return Poset((names + joins + [top], covers), cover_relations=True)


semi_labels = {"1": r"$\semifancpt{F_T}{\mcf_\bullet^1}$", "2": r"$\semifancpt{F_T}{\mcf_\bullet^2}$",
               "3": r"$\semifancpt{F_T}{\mcf_\bullet^3}$", "4": r"$\semifancpt{F_T}{\mcf_\bullet^4}$",
               "12": r"$\semifancpt{F_T}{\mcf_\bullet^{1,2}}$", "23": r"$\semifancpt{F_T}{\mcf_\bullet^{2,3}}$",
               "34": r"$\semifancpt{F_T}{\mcf_\bullet^{3,4}}$", "top": r"$\semitorcpt{F_T}$"}
poset_json(chain_of_joins(["1", "2", "3", "4"], "top"), "semitoroidal.json",
           name=str, label=lambda x: semi_labels[x], order=lambda x: (len(x), x))

tor_labels = {"1": r"$\semifancpt{F_T}{\Sigma_\bullet^1}$", "2": r"$\semifancpt{F_T}{\Sigma_\Cox}$",
              "3": r"$\semifancpt{F_T}{\Sigma_\bullet^3}$", "12": r"$\semifancpt{F_T}{\Sigma_\bullet^{1,2}}$",
              "23": r"$\semifancpt{F_T}{\Sigma_\bullet^{2,3}}$", "top": r"$\torcpt{F_T}$"}
poset_json(chain_of_joins(["1", "2", "3"], "top"), "toroidal.json",
           name=str, label=lambda x: tor_labels[x], order=lambda x: (len(x), x),
           style=lambda x: "fill=dzg highlight" if x == "2" else "")
