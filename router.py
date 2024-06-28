import math


class router:
    cmd = 1
    __precursor_matrix = [[]]
    __neighbour_matrix = [[]]
    __distance = [[]]
    def __init__(self, neighbour_matrix,distance):
        self.__neighbour_matrix = neighbour_matrix
        self.__distance = distance
    ## 查询端到端路由
    def get_next(self, src, dst):
        return self.__precursor_matrix[src][dst]

    ## 查询端到所有路由
    def get_next_src(self, src):
        return self.__precursor_matrix[src]

    ##
    def cal_n(self):
        num_satellites = len(self.__neighbour_matrix)
        for i in range(num_satellites):
            for j in range(num_satellites):
                if (i != j) & (j not in self.__neighbour_matrix[i]):
                    # print(i,j,self.__neighbour_matrix[i])
                    min_cost = math.inf
                    for neighbour in self.__neighbour_matrix[i]:
                        if self.__distance[i][neighbour] + self.__distance[neighbour][j] < min_cost:
                            min_cost = self.__distance[i][neighbour] + self.__distance[neighbour][j]
                            # print(i,j,neighbour,parents[i][j], parents[neighbour][j])
                            self.__distance[i][j] = min_cost

        predecessor = [[-1 for i in range(num_satellites)] for j in range(num_satellites)]
        for i in range(num_satellites):
            for j in range(num_satellites):
                flag = 0
                if i != j:  # & (j not in neighbour_matrix[i]):
                    # print(i,j,self.__neighbour_matrix[i])
                    for neighbour in self.__neighbour_matrix[i]:
                        if (
                                self.__distance[i][neighbour] + self.__distance[neighbour][j]
                                == self.__distance[i][j]
                        ):
                            # min_cost = graph[i][neighbour] + graph[neighbour][j]
                            # print(i,j,neighbour,parents[i][j], parents[neighbour][j])
                            predecessor[i][j] = neighbour
                            # flag = 1
                            break
                    # if flag!=1 :
                    #     print("error",i,j,distance[i][neighbour],distance[neighbour][j],distance[i][j])
        self.__precursor_matrix = predecessor
        print("===========self.__distance===========")
        for row in self.__distance:
            print(row)
