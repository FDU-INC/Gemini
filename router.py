import math
from abc import abstractmethod


class Router:

    @abstractmethod
    def cal_n(self):
        print("error")
        exit(0)

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

    def set_neighbour_matrix(self, neighbour_matrix):
        self.neighbour_matrix = neighbour_matrix

    def set_distance(self, distance):
        self.distance = distance

    def set_all(self, neighbour_matrix, distance):
        self.neighbour_matrix = neighbour_matrix
        self.distance = distance

    def __init__(self, neighbour_matrix=None, distance=None):
        if neighbour_matrix is None:
            neighbour_matrix = [[]]
        if distance is None:
            distance = [[]]
        self.neighbour_matrix = neighbour_matrix
        self.distance = distance
        self.precursor_matrix = [[-1 for i in range(len(distance))] for j in range(len(distance))]


class FloydRouter(Router):

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


class FastRouter(Router):

    def __init__(self, neighbour_matrix, distance, gs_no_list):
        super().__init__(neighbour_matrix, distance)
        self.sat_distance = None
        self.gs_neighbour_matrix = None
        self.sat_neighbour_matrix = None
        self.gs_sat_distance = None
        self.gs_no_list = gs_no_list
        print(self.gs_no_list)
        self.gs_sat_divide()

    def set_all(self, neighbour_matrix, distance):
        self.neighbour_matrix = neighbour_matrix
        self.distance = distance
        self.gs_sat_divide()

    def gs_sat_divide(self):
        if (self.gs_no_list[-1] != len(self.neighbour_matrix) - 1) | (
                self.gs_no_list[-1] - self.gs_no_list[0] != len(self.gs_no_list) - 1):
            print("gs_no_list error")
            exit(0)

        self.gs_neighbour_matrix = []
        self.sat_neighbour_matrix = []
        self.sat_distance = []
        self.gs_sat_distance = []
        gs_num = len(self.gs_no_list)
        sat_num = len(self.neighbour_matrix) - gs_num
        for i in range(len(self.neighbour_matrix)):
            if i in self.gs_no_list:  # 地面站
                self.gs_neighbour_matrix.append(self.neighbour_matrix[i])  # 加入邻接矩阵（卫星）
                self.gs_sat_distance.append(self.distance[i][0:sat_num])  # 加入距离矩阵（卫星）
            else:
                self.sat_neighbour_matrix.append([j for j in self.neighbour_matrix[i] if j not in self.gs_no_list])
                self.sat_distance.append(self.distance[i][0:sat_num])

    def cal_gs(self):
        num_gs = len(self.gs_neighbour_matrix)
        num_satellites = len(self.sat_neighbour_matrix)

        for i in range(num_gs):
            gs_index = i + num_satellites

            for sat_num in range(num_satellites):
                if sat_num in self.gs_neighbour_matrix[i]:
                    self.precursor_matrix[gs_index][sat_num] = sat_num
                    self.precursor_matrix[sat_num][gs_index] = gs_index
                else:
                    min_cost = math.inf
                    for neighbour in self.gs_neighbour_matrix[i]:
                        if self.distance[gs_index][neighbour] + self.distance[neighbour][sat_num] < min_cost:
                            min_cost = self.distance[gs_index][neighbour] + self.distance[neighbour][sat_num]
                            self.distance[gs_index][sat_num] = min_cost
                            self.distance[sat_num][gs_index] = min_cost
                            self.precursor_matrix[gs_index][sat_num] = neighbour
                            self.precursor_matrix[sat_num][gs_index] = self.precursor_matrix[sat_num][neighbour]
                    # print(i,sat_num,self.distance[gs_index][sat_num],self.precursor_matrix[gs_index][sat_num],self.precursor_matrix[sat_num][gs_index])

        # print("In mid")
        # self.print_distance()
        # # cal gs-gs
        for i in range(num_gs):
            for j in range(i + 1, num_gs):
                src_gs = i + num_satellites
                tag_gs = j + num_satellites
                min_cost = math.inf
                for neighbour in self.gs_neighbour_matrix[i]:
                    if self.distance[src_gs][neighbour] + self.distance[neighbour][tag_gs] < min_cost:
                        min_cost = self.distance[src_gs][neighbour] + self.distance[neighbour][tag_gs]
                        self.distance[src_gs][tag_gs] = min_cost
                        self.distance[tag_gs][src_gs] = min_cost
                        self.precursor_matrix[src_gs][tag_gs] = neighbour
                        self.precursor_matrix[tag_gs][src_gs] = self.precursor_matrix[tag_gs][neighbour]

    def cal_sat(self):
        num_satellites = len(self.sat_neighbour_matrix)
        for i in range(num_satellites):
            for neighbour in self.sat_neighbour_matrix[i]:
                self.precursor_matrix[i][neighbour] = neighbour
        for k in range(num_satellites):
            for i in range(num_satellites):
                for j in range(num_satellites):
                    if self.distance[i][k] + self.distance[k][j] < self.distance[i][j]:
                        # print(i,j,neighbour,parents[i][j], parents[neighbour][j])
                        self.distance[i][j] = self.distance[i][k] + self.distance[k][j]
                        self.precursor_matrix[i][j] = self.precursor_matrix[i][k]

    def cal_n(self):
        num_nodes = len(self.neighbour_matrix)
        self.precursor_matrix = [[-1 for i in range(num_nodes)] for j in range(num_nodes)]
        self.cal_sat()
        self.cal_gs()
        # self.print_distance()
        # self.print_precursor_matrix()
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
