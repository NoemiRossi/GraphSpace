import pandas as pd
from matcher import Matcher
import docplex.mp.model as cpx
from sklearn.metrics.pairwise import pairwise_distances

# Docplex approach

# GAS is a child of matcher
# GAS algorithm is used to compute the match between two networks through the usage of
# docplex python package and the cplex solver
# Giving two input networks, the algorithm choose the best matching between nodes by
# solving the associated optimization problem, minimizing the sum of pairwise distances
# between both nodes and edges. The input of cplex is a pairwise distance matrix.

# GAS1 would like to improve the performance of GAS by making the optimization problem linear
# More variables and constraints are introduced.

class GAS1(Matcher):

    def __init__(self,X=None,Y=None,f=None):
        Matcher.__init__(self,X,Y,f)
        self.name="Gaaaaaaas! - Linear"
        
    
    # The match function: this function find the best match among the equivalent classes
    def match(self,X,Y):
        # Take the two graphs - they have already the same size
        self.X=X
        self.Y=Y
        
        nX=self.X.nodes()

        # set of non-zero nodes (i,i) that are in X or in Y
        # note. assuming that if there is an edge (i,j), both i and j have non-zero attribute
        isetn = set((i, j) for ((i, j), y) in self.X.x.items() if y != [0] if i == j).union(
            set((i, j) for ((i, j), y) in self.Y.x.items() if y != [0] if i == j))
        isetn = sorted(isetn)
        # set of indices i of non-zero nodes (i,i) that are in X or in Y
        isetnn = [i for (i, j) in isetn]
        # set of edges btw non-zero nodes that are in X or in Y
        isete = [(i, j) for i in isetnn for j in isetnn if i != j]

        # building up the matrix of pairwise distances btw nodes:
        x_vec_n = self.X.to_vector_with_select_nodes(isetn)
        y_vec_n = self.Y.to_vector_with_select_nodes(isetn)
        gas_n = pd.DataFrame(pairwise_distances(x_vec_n,
                                                y_vec_n),
                             columns=y_vec_n.index,
                             index=x_vec_n.index)
        del x_vec_n, y_vec_n

        # building up the matrix of pairwise distances btw edges:
        x_vec_e = self.X.to_vector_with_select_edges(isete)
        y_vec_e = self.Y.to_vector_with_select_edges(isete)
        gas_e = pd.DataFrame(pairwise_distances(x_vec_e,
                                                y_vec_e) + 0.01,
                             # see below in the constraints the reason behind 0.01
                             columns=y_vec_e.index,
                             index=x_vec_e.index)
        del x_vec_e, y_vec_e
        
        # optimization model:

        # initialize the model
        # opt_model = cpx.Model(name="HP Model")
        opt_model = cpx.Model(name="HP Model", ignore_names=True, checker='off') # faster

        # list of binary variables: 1 if i match j, 0 otherwise
        # x_vars is n x n x n x n
        x_vars = {(i, j, u, v): opt_model.binary_var(name="x_{0}_{1}_{2}_{3}".format(i, j, u, v))
                  for i in isetnn for j in isetnn for u in isetnn for v in isetnn}

        ## constraints
        # one to one correspondence between the nodes in the two networks
        opt_model.add_constraints( (opt_model.sum(x_vars[i,i,u,u] for i in isetnn)== 1 for u in isetnn),
                                  ("constraint_r{0}".format(u) for u in isetnn) )

        opt_model.add_constraints( (opt_model.sum(x_vars[i,i,u,u] for u in isetnn)== 1 for i in isetnn),
                                  ("constraint_c{0}".format(i) for i in isetnn)  )

        # we want to have: x_iu = 1 and x_jv = 1 <==> x_ijuv=1
        # the constraint x_iu = 1 and x_jv = 1 ==> x_ijuv=1 is written as x_ijuv >= x_iu + x_jv -1
        opt_model.add_constraints( ( x_vars[i,j,u,v] - x_vars[i,i,u,u] - x_vars[j,j,v,v]>= -1
                                     for (i, j) in isete
                                     for (u, v) in isete),
                                   ("constraint_e{0}_{1}_{2}_{3}".format(i,j,u,v)
                                    for (i, j) in isete
                                    for (u, v) in isete)  )
        # to have also the opposite implication, we force x_ijuv to be zero
        # by adding a constant in the objective function - which has to be minimized
        # more precisely, we add a 0.01 directly to the gas_e matrix


        # objective function - sum the distance between nodes and the distance between edges
        # e.g. (i,i) is a node in X, (u,u) is a node in Y, (i,j) is an edge in X, (u,v) is an edge in Y.
        objective = opt_model.sum(x_vars[i,i,u,u] * gas_n.loc['({0}, {0})'.format(i), '({0}, {0})'.format(u)]
                                  for i in isetnn
                                  for u in isetnn) + opt_model.sum(
            x_vars[i, j, u, v] * (gas_e.loc['({0}, {1})'.format(i, j),
                                            '({0}, {1})'.format(u, v)])
            for (i, j) in isete   # for i in isetnn for j in isetnn if j!=i
            for (u, v) in isete)  # for u in isetnn for v in isetnn if v!=u

        # Minimizing the distances as specified in the objective function
        opt_model.minimize(objective)
        # Finding the minimum
        opt_model.solve()

        # Save in f the permutation: <3
        ff = [(i, u) for (i, j, u, v), z in x_vars.items() if z.solution_value == 1 if i == j if u == v]
        if len(ff) < nX:
            # if the number of nodes involved in the matching, i.e. non-zero nodes, is smaller than the total,
            # set up the permutation vector in the proper way
            # e.g. X nodes 1,3 Y nodes 1,4 -> isetnn={1,3,4} -> len(x_vars>0)=3
            # -> i want to avoid st. like f=[4,1,3] because i want len(f)=nX
            self.f = list(range(nX))
            for (i, u) in ff:
                self.f[i] = u
        else:
            self.f = [u for (i, u) in ff]

        del gas_n, gas_e

        # <3
 
            

