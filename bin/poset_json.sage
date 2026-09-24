# Writes a finite Sage poset as the networkx node-link JSON that
# \posetfromjson (styles/macros/tikz/constructors/dzg-posets.tex) draws.
#
#   load("~/.pandoc/bin/poset_json.sage")
#   poset_json(posets.DivisorLattice(24), "div24.json",
#              label=lambda d: "$%s$" % d, name=lambda d: "d%s" % d)
#
# label(x): the TeX text in x's box (default: empty, for figures that place
#   their own content at every element).
# name(x): the TikZ node name of x (default: e<k>, k the index of x in P);
#   letters, digits, - and _ only.
# graded: write P.rank_function() as each element's grade (default: when P
#   is graded); otherwise the layout computes a grading.
import json
import networkx as nx


def poset_json(P, path, label=None, name=None, graded=None):
    index = {x: k for k, x in enumerate(P)}
    name = name or (lambda x: "e%d" % index[x])
    if graded is None:
        graded = P.is_graded()
    rank = P.rank_function() if graded else None
    G = nx.DiGraph()
    for x in P:
        data = {"label": label(x) if label else ""}
        if rank is not None:
            data["grade"] = int(rank(x))
        G.add_node(name(x), **data)
    for lower, upper in P.cover_relations():
        G.add_edge(name(lower), name(upper))
    with open(path, "w") as handle:
        json.dump(nx.node_link_data(G, edges="links"), handle)
