# The poset of subdiagrams of the Coxeter diagram C(L) of the lattice with
# root Gram matrix G_L below, ordered by inclusion; writes subdiagrams-C-L.json
# for \posetfromjson (figures/tikz/large_subdiagram_poset.tex).
#
#       3 == 4 === 5        1-2, 1-3, 2-3: (r_i, r_j) = 1   (weight 3)
#      / \                  3-4:           (r_3, r_4) = 2   (weight 4)
#     1---2                 4-5:           (r_4, r_5) = 4   (weight infinity)
#
# Roots 1, 2, 3 have square -2, roots 4, 5 square -4; G_L has signature
# (1, 4) and determinant 48. A subdiagram is a subset of {1, ..., 5}, named by
# its bitmask m = sum of 2^(i-1) over its vertices i and graded by its size.
# Its type, the style of its cell: elliptic when -G_L on the subset is
# positive definite; parabolic when it is positive semidefinite and every
# connected component is affine (corank 1), which holds for {1,2,3} = A~_2
# and {4,5} = A~_1 only, both maximal; other otherwise (A~_2 + A_1 and
# A~_1 + A_1 among them, whose elliptic component is not affine).
#
#   sage subdiagrams-C-L.sage
load("~/.pandoc/bin/poset_json.sage")
G = matrix(ZZ, [[-2, 1, 1, 0, 0], [1, -2, 1, 0, 0], [1, 1, -2, 2, 0],
                [0, 0, 2, -4, 4], [0, 0, 0, 4, -4]])
assert G.det() == 48 and sum(1 for e in G.change_ring(RDF).eigenvalues() if e > 0) == 1


def components(S):
    left, comps = list(S), []
    while left:
        stack = [left.pop()]
        comp = list(stack)
        while stack:
            v = stack.pop()
            for u in [u for u in left if G[v, u] != 0]:
                left.remove(u)
                comp.append(u)
                stack.append(u)
        comps.append(comp)
    return comps


def subdiagram_type(m):
    S = [i for i in range(5) if m >> i & 1]
    if not S or (-G.matrix_from_rows_and_columns(S, S)).is_positive_definite():
        return "elliptic"
    if (-G.matrix_from_rows_and_columns(S, S)).is_positive_semidefinite() and all(
            G.matrix_from_rows_and_columns(c, c).rank() == len(c) - 1 for c in components(S)):
        return "parabolic"
    return "other"


assert [m for m in range(32) if subdiagram_type(m) == "parabolic"] == [7, 24]
P = Poset((list(range(32)), lambda a, b: a & b == a))
poset_json(P, "subdiagrams-C-L.json", name=str,
           style=lambda m: "subdiagram cell=" + subdiagram_type(m),
           order=lambda m: (bin(m).count("1"), [i for i in range(5) if m >> i & 1]))
