# The stratification poset of \overline{M}_2 (Deligne-Mumford), by topological
# type; writes m2-strata.json for \posetfromjson.
#
# \overline{M}_2 has dimension 3 and seven strata, one for each stable graph of
# genus 2: a connected graph with vertex genera g_v, possibly with loops, such
# that sum g_v + h^1 = 2 and every genus-0 vertex has valence >= 3. A stratum
# with n nodes (edges) has dimension 3 - n. The closure order is edge
# contraction: the stratum of G lies in the closure of the stratum of G/e.
# Enumeration by n (Harris-Morrison, "Moduli of curves", Sec. 3.C):
#   n = 0  one genus-2 vertex                                     (smooth)
#   n = 1  two genus-1 vertices, one edge                         (Delta_1)
#          one genus-1 vertex, one loop                           (Delta_0)
#   n = 2  genus-1 vertex, edge, genus-0 vertex with a loop
#          one genus-0 vertex, two loops
#   n = 3  two genus-0 vertices, one edge, a loop at each         (dumbbell)
#          two genus-0 vertices, three edges                      (theta)
#
# Each stratum is named by a divisor d of 24 = 2^3 * 3, d = 2^k * 3^c with
# (k, c) a nonempty subdiagram of the Coxeter diagram objects/moduli/m2-coxeter
# up to its S_3 symmetry: k of the three black vertices and c of the white
# centre. d -> stratum is an isomorphism of Div(24) \ {1}, ordered by
# divisibility, onto the stratification poset, with dim = (number of prime
# factors of d, with multiplicity) - 1:
#   d    dim  stratum
#   24   3    smooth
#   8    2    Delta_1                      (closure: 4, 2)
#   12   2    Delta_0                      (closure: 4, 6, 2, 3)
#   4    1    elliptic + nodal rational    (closure: 2)
#   6    1    rational with two nodes      (closure: 2, 3)
#   2    0    dumbbell
#   3    0    theta
# The rank of the poset is the dimension; stratum d is drawn by the objects
# m2-graph-d and m2-curve-d.
#
#   sage m2-strata.sage
load("~/.pandoc/bin/poset_json.sage")
P = posets.DivisorLattice(24).subposet([d for d in divisors(24) if d > 1])
assert all(P.rank(d) == sum(e for _, e in factor(d)) - 1 for d in P)
poset_json(P, "m2-strata.json", label=lambda d: "$%s$" % d, name=lambda d: str(d))
