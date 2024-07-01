import math
from abc import abstractmethod


class Router:

    @abstractmethod
    def cal_n(self):
        print("error")
        pass

    def print_distance(self):
        print("===========self.__distance===========")
        for row in self.distance:
            print(row)

    def print_precursor_matrix(self):
        print("===========self.__precursor_matrix===========")
        for row in self.precursor_matrix:
            print(row)

    def print_neighbor_matrix(self):
        print("===========self.__neighbour_matrix===========")
        for row in self.neighbour_matrix:
            print(row)

    def get_next(self, src, dst):
        return self.precursor_matrix[src][dst]

    ## 查询端到所有路由
    def get_next_src(self, src):
        return self.precursor_matrix[src]

    def __init__(self, neighbour_matrix=None, distance=None):
        if neighbour_matrix is None:
            neighbour_matrix = [[]]
        if distance is None:
            distance = [[]]
        self.neighbour_matrix = neighbour_matrix
        self.distance = distance
        self.precursor_matrix = [[-1 for i in range(len(distance))] for j in range(len(distance))]


class FloydRouter(Router):
    cmd = 1

    def __init__(self, neighbour_matrix, distance):
        super().__init__(neighbour_matrix, distance)

        # print("distance:", self.distance)
        # print("precursor:",self.precursor_matrix)

    ## 查询端到端路由

    ##
    def cal_n(self):
        num_satellites = len(self.neighbour_matrix)
        self.precursor_matrix = [[-1 for i in range(num_satellites)] for j in range(num_satellites)]
        for i in range(num_satellites):
            for neighbour in self.neighbour_matrix[i]:
                self.precursor_matrix[i][neighbour] = neighbour
        for k in range(num_satellites):
            for i in range(num_satellites):
                for j in range(num_satellites):
                    if self.distance[i][k] + self.distance[k][j] < self.distance[i][j]:
                        # print(i,j,neighbour,parents[i][j], parents[neighbour][j])
                        self.distance[i][j] = self.distance[i][k] + self.distance[k][j]
                        self.precursor_matrix[i][j] = self.precursor_matrix[i][k]
        # for i in range(num_satellites):
        #     for j in range(num_satellites):
        #         if (i != j) & (j not in self.__neighbour_matrix[i]):
        #             # print(i,j,self.__neighbour_matrix[i])
        #             min_cost = math.inf
        #             # for neighbour in self.__neighbour_matrix[i]:
        #             for neighbour in range(num_satellites):
        #                 if self.__distance[i][neighbour] + self.__distance[neighbour][j] < min_cost:
        #                     min_cost = self.__distance[i][neighbour] + self.__distance[neighbour][j]
        #                     # print(i,j,neighbour,parents[i][j], parents[neighbour][j])
        #                     self.__distance[i][j] = min_cost

        # predecessor = [[-1 for i in range(num_satellites)] for j in range(num_satellites)]
        # for i in range(num_satellites):
        #     for j in range(num_satellites):
        #         flag = 0
        #         if i != j:  # & (j not in neighbour_matrix[i]):
        #             # print(i,j,self.__neighbour_matrix[i])
        #             for neighbour in self.__neighbour_matrix[i]:
        #                 if (
        #                         self.__distance[i][neighbour] + self.__distance[neighbour][j]
        #                         == self.__distance[i][j]
        #                 ):
        #                     # min_cost = graph[i][neighbour] + graph[neighbour][j]
        #                     # print(i,j,neighbour,parents[i][j], parents[neighbour][j])
        #                     predecessor[i][j] = neighbour
        #                     # flag = 1
        #                     break
        #             # if flag!=1 :
        #             #     print("error",i,j,distance[i][neighbour],distance[neighbour][j],distance[i][j])
        # self.__precursor_matrix = predecessor
