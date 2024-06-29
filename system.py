import json

from skyfield.api import load, wgs84
import skyfield.positionlib as pos
import math
import os
import socket
from enum import Enum
import time
from datetime import datetime, timezone
import subprocess

from typing import Dict

from host import Host
from router import router
import json

FAST_ROUTE = False

DEBUG = True
CONTAINER_DICT = {}
HOST_INSTANCE_DICT = {}
HOST_NAME_FROM_IP = {}


def do_cmd(cmd):
    host_ip = cmd[0: cmd.find(":")]
    real_cmd = cmd[cmd.find(":") + 2:]
    host = HOST_INSTANCE_DICT[HOST_NAME_FROM_IP[host_ip]]
    # print(host_ip)
    # print(real_cmd)
    # print(real_cmd)
    if not DEBUG:
        return host.execute(real_cmd)
        pass
    else:
        # print(host_ip, real_cmd)
        pass
    # print(cmd+host.execute(real_cmd))


class NodeType(Enum):
    Ground = 0
    Up = 1
    Down = 2
    Left = 3
    Right = 4


class Container:
    def __init__(
            self, container_name, exist, port, ip="", mac="", ip_host="", port_out=0
    ):
        self.exist = exist
        self.ip = ip  ## container_ip
        self.ip_host = ip_host  ## host ip
        self.mac = mac
        self.container_name = container_name
        self.port = port
        self.port_out = port_out
        self.filter_exist = {
            1: False,
            2: False,
            3: False,
            4: False,
        }  # NodeType-1 -> index ground_index-4 = index
        if self.ip == local_ip:
            self.remote = False
        else:
            self.remote = True
        self.init_eth("enp1s0")
        # print(self.mac)

    def init_eth(self, eth_name):
        cmd01 = self.ip + ": tc qdisc add dev " + eth_name + " root handle 1: htb"
        cmd02 = (
                self.ip
                + ": tc class add dev "
                + eth_name
                + " parent 1: classid 1:1 htb rate 50mbit"
        )
        do_cmd(cmd01)
        do_cmd(cmd02)

    def add_eth_queue_delay(self, eth_name, index, delay):  # eth_name-str  delay-float
        cmd = (
                self.ip
                + ": tc class add dev "
                + eth_name
                + " parent 1:1 classid 1:"
                + str(index)
                + "0 htb rate 10mbit"
        )
        do_cmd(cmd)
        cmd = (
                self.ip
                + ": tc qdisc add dev "
                + eth_name
                + " parent 1:"
                + str(index)
                + "0 netem delay "
                + str(delay)
                + "ms"
        )
        self.filter_exist[index] = True
        do_cmd(cmd)

    def modify_eth_queue_delay(self, eth_name, index, delay):  # ip-str delay-float
        cmd = (
                self.ip
                + ": tc qdisc change dev "
                + eth_name
                + " parent 1:"
                + str(index)
                + "0 netem delay "
                + str(delay)
                + "ms"
        )
        do_cmd(cmd)

    def set_eth_queue_delay(self, eth_name, index, delay):
        index = index + 1  # 1：0 can not be used as class id in tc
        if not self.exist:
            return

        if self.filter_exist.get(index) and self.filter_exist[index]:
            self.modify_eth_queue_delay(eth_name, index, delay)
        else:
            self.add_eth_queue_delay(eth_name, index, delay)

    # set ofctl
    def set_ovs_flow(self, src_port, dst_ip, nxt_port, nxt_mac):
        if not self.exist:
            return
        if nxt_mac == "":
            cmd = "{}: ovs-ofctl add-flow br0 ip,in_port={},nw_dst={},actionsoutput:{}".format(
                self.ip_host, src_port, dst_ip, nxt_port
            )
        else:
            cmd = "{}: ovs-ofctl add-flow br0 ip,in_port={},nw_dst={},actions=mod_dl_dst:{},output:{}".format(
                self.ip_host, src_port, dst_ip, nxt_mac, nxt_port
            )
        do_cmd(cmd)

    def set_tc_filter(self, dst, index):
        # ip to 16进制数
        dst_16 = socket.inet_aton(dst).hex()
        # print(dst_16)
        cmd = (
            '{}: tc filter del dev enp1s0 parent 1: prio 1 handle $(tc filter list dev enp1s0 | grep -B1 "{}" | '
            "head -1 |  awk '{{print $12}}') u32 ; tc filter"
            " add dev enp1s0 protocol ip parent 1: prio 1 u32 match ip dst {} flowid 1:{}0"
        ).format(self.ip, dst_16, dst, index)
        # print(cmd)
        do_cmd(cmd)

    def get_ping_delay(self, dst_ip):
        cmd = "{}: ping {} -c 1 | grep time= | awk '{{print $7}}'".format(
            self.ip, dst_ip
        )
        result = do_cmd(cmd)
        result = result.strip().split("=")
        if (len(result) != 2):
            delay = math.inf
        else:
            delay = float(result[1])
        return delay


class GroundStation:
    def __init__(self, name, loc, typ, no):
        self.name = name
        self.loc = loc
        self.typ = typ  # ue or core
        self.no = no


class Node:
    def __init__(self, name, typ, system, no=0):
        self.system = system
        self.name = name
        self.neighbor = dict()
        self.bridgeName = ""
        self.subnet = ""
        self.typ = typ  # ue or core or gnb
        self.interfaceName = ""
        self.groundMax = 0
        self.bridgeName = "b" + self.name
        self.index_dict = dict()
        self.no = no
        self.pre = []
        # print(no)

    def find_first_idle_ground(self):
        if self.groundMax <= 0:
            return -1
        for i in range(self.groundMax):
            if self.index_dict.get(i + 4) is None:
                return i+4
        return -1

    def add_neighbor(self, node, type=NodeType.Ground):
        if not self.neighbor.get(node.name):
            # print(node.name)
            if type != NodeType.Ground:
                neighborNode = NodeInfo(node, type)
                index = type.value - 1
            else:
                index = self.find_first_idle_ground()
                # print(self.groundMax)
                if index < 0:
                    # print(self.name, "not found space", self.groundMax)
                    self.groundMax += 1
                    index = self.groundMax - 1 + 4
                # print(index)
                neighborNode = NodeInfo(node, type, index)
            # print("add {} to {}, index ={}".format(node.name, self.name, neighborNode.index))
            self.neighbor.update({node.name: neighborNode})
            self.index_dict.update({index: node.name})
        else:
            return
            # print("node {} already in".format(node.name))

    def print_neigbour(self):
        print("node {}'s neighbour".format(self.name))
        for nodeInfo in self.neighbor.values():
            print("{}: index= {}".format(nodeInfo.node.name, nodeInfo.index))

    def del_neighbor(self, node_name):
        # self.print_neigbour()
        node = self.neighbor.get(node_name)
        if node is None:
            print("no node {} to del".format(node_name))
        else:
            if node.isConnected:
                # release the connection
                print("1")
            # print(self.index_dict)

            try:
                i = node.index
                self.neighbor.pop(node_name)

                self.index_dict.pop(i)

            except Exception as error:
                print("error:" + str(error))
                print(node_name)
                print(i)

    # for all node in neighbour, find the node that not set delay and set
    def set_delay_all(self):
        for node in self.neighbor.values():
            if not node.delay_set:
                self.set_delay(node)

    def set_delay(self, nodeI):
        # print(self.interfaceName)

        CONTAINER_DICT[self.name].set_eth_queue_delay(
            self.interfaceName, nodeI.index, nodeI.delay
        )
        nodeI.delay_set = True

    def update_delay(self, name, delay):
        node = self.neighbor.get(name)
        if node is None:
            print("no node" + " {} to update".format(name))
        else:
            node.delay = delay
            node.delay_set = False

    def set_pre(self, pre):
        self.pre = pre
        c1 = CONTAINER_DICT[self.name]
        for i in range(len(pre)):
            if pre[i] == -1:
                continue
            dst_name = self.system.node_num_dict[i].name
            nxt_name = self.system.node_num_dict[pre[i]].name
            c2 = CONTAINER_DICT[dst_name]
            c3 = CONTAINER_DICT[nxt_name]
            if c3.ip_host == c1.ip_host:  # same host
                # print(c1.mac, c2.mac, c3.mac)
                c1.set_ovs_flow(c1.port, c2.ip, c3.port, c3.mac)
            else:
                c1.set_ovs_flow(c1.port, c2.ip, c1.port_out, c3.mac)
                c3.set_ovs_flow(c3.port_out, c2.ip, c3.port, "")
            # print(nxt_name)
            # print(self.neighbor)
            try:
                neighbourInfo = self.neighbor.get(nxt_name)
                c1.set_tc_filter(c2.ip, neighbourInfo.index + 1)
            except Exception as e:
                print(e)
                print("error " + self.name + " " + nxt_name)
                print(self.neighbor)

    def get_ping_delay(self, dst_node):
        return CONTAINER_DICT[self.name].get_ping_delay(
            CONTAINER_DICT[dst_node.name].ip
        )


class NodeInfo:
    def __init__(self, node, type=NodeType.Ground, g_index=0):
        self.node = node
        self.isConnected = False
        self.type = type
        self.delay = 0
        self.delay_set = False
        if type == NodeType.Ground:
            self.index = g_index
        else:
            self.index = type.value - 1

    def connect(self):
        if self.isConnected:
            print("error! node {} has been connected".format(self.node.name))
        self.isConnected = True


class SatelliteSystem:
    def __init__(self, url, gs_position, use_real_data):
        self.router = None
        self.node_num_dict = None
        self.from_real = use_real_data  # 是否是真实数据
        self.tle_url = url if use_real_data else "three.tle"
        self.neighbour_matrix = [[]]
        self.distance = [[]]
        self.satellites = None
        self.satellites_name_dict = None
        self.satellites_num_dict = None
        self.gs_position = gs_position
        self.gss = None
        self.gs_list = []
        self.orbit_num = None
        self.orbit_satellite = None
        self.docker_list = None
        self.satellite_num_orbit = None
        self.sim_start_time = time.time()
        self.time_acceleration = 50
        self.node_dict = dict[str:Node]()
        self.init()
        self.run()

    def init(self):
        """
        description: 初始化卫星和地面站信息
        :return: None
        """
        utc_time = datetime.utcfromtimestamp(self.sim_start_time).replace(
            tzinfo=timezone.utc
        )
        ts = load.timescale()
        t = ts.utc(utc_time)
        self.satellites = self.load_tle(self.tle_url)
        self.satellites_name_dict = {sat.name: sat for sat in self.satellites}
        self.satellites_num_dict = {sat.model.satnum: sat for sat in self.satellites}
        # build for gs_list
        self.gss = self.create_gs(self.gs_position)
        for i, gs in enumerate(self.gss):
            typ = "core" if i == 0 else "ue"
            self.gs_list.append(
                GroundStation("GroundStation-" + typ + str(i), gs, typ, i)
            )
        # node_dict加sat 序号i递增
        self.node_dict = {
            self.satellites_num_dict[no].name: Node(
                self.satellites_num_dict[no].name, "gnb", self, no - 1
            )
            for no in self.satellites_num_dict
        }
        self.node_dict.update(
            {
                gs.name: Node(
                    gs.name, gs.typ, self, gs.no + len(self.satellites_num_dict)
                )
                for gs in self.gs_list
            }
        )
        self.node_num_dict = {node.no: node for node in self.node_dict.values()}
        self.load_hosts_instance()
        self.clean_orbits(t)
        self.node_init(t)
        return

    def renew_delay_update_all_route(self, t):
        self.neighbour_matrix = [[] for i in range(len(self.node_dict))]
        self.distance = [
            [math.inf for i in range(len(self.node_dict))]
            for j in range(len(self.node_dict))
        ]
        for node in self.node_dict.values():
            self.distance[node.no][node.no] = 0
            ## 处理卫星节点
            direction = [NodeType.Up, NodeType.Down, NodeType.Left, NodeType.Right]
            neighbours = self.get_neighbour_satellite(node.name)
            if neighbours is not None:  # check if it's a satellite
                for nd in node.neighbor.values():
                    delay = 0
                    if nd.type in direction:
                        delay = self.get_interlink_delay(node.name, nd.node.name, t)
                    elif nd.type == NodeType.Ground:
                        gs_new = None
                        for gs_ in self.gs_list:
                            if gs_.name == nd.node.name:
                                gs_new = gs_
                        delay = self.get_sat_earth_link_delay(node.name, gs_new, t)
                        self.neighbour_matrix[nd.node.no].append(node.no)
                        self.distance[nd.node.no][node.no] = delay
                    self.neighbour_matrix[node.no].append(nd.node.no)
                    self.distance[node.no][nd.node.no] = delay
        self.router = router(self.neighbour_matrix, self.distance)
        print(self.neighbour_matrix)
        print(self.distance)
        for gs in self.gs_list:
            print(gs.name)
            print(self.neighbour_matrix[self.node_dict[gs.name].no])
            print(self.node_dict[gs.name].neighbor.keys())
            if len(self.neighbour_matrix[self.node_dict[gs.name].no]) != len(self.node_dict[gs.name].neighbor.keys()):
                exit(0)
        self.router.cal_n()
        self.set_all_router()

    def node_init(self, t):
        self.load_containers()
        if FAST_ROUTE:
            self.gs_neighbour_matrix = [[] for i in range(len(self.gs_list))]
            self.gs_distance = [
                [math.inf for i in range(len(self.satellites_num_dict))]
                for j in range(len(self.gs_list))
            ]
            self.neighbour_matrix = [[] for i in range(len(self.satellites_num_dict))]
            self.distance = [
                [math.inf for i in range(len(self.satellites_num_dict))]
                for j in range(len(self.satellites_num_dict))
            ]
        else:
            self.neighbour_matrix = [[] for i in range(len(self.node_dict))]
            self.distance = [
                [math.inf for i in range(len(self.node_dict))]
                for j in range(len(self.node_dict))
            ]
        for node in self.node_dict.values():
            self.distance[node.no][node.no] = 0

            neighbours = self.get_neighbour_satellite(node.name)
            direction = [NodeType.Up, NodeType.Down, NodeType.Left, NodeType.Right]
            if neighbours is not None: ## 处理卫星节点
                for i in range(len(neighbours)):
                    node.add_neighbor(self.node_dict.get(neighbours[i]), direction[i])
                gs_list = self.get_connect_gs(node.name, t)
                for gs in gs_list:
                    node.add_neighbor(self.node_dict.get(gs.name))
                    self.node_dict[gs.name].add_neighbor(node)
                for nd in node.neighbor.values():
                    delay = 0
                    if nd.type in direction:
                        delay = self.get_interlink_delay(node.name, nd.node.name, t)
                        if FAST_ROUTE:
                            self.neighbour_matrix[node.no].append(nd.node.no)
                            self.distance[node.no][nd.node.no] = delay
                    elif nd.type == NodeType.Ground:
                        gs_new = None
                        for gs_ in self.gs_list:
                            if gs_.name == nd.node.name:
                                gs_new = gs_
                        delay = self.get_sat_earth_link_delay(node.name, gs_new, t)
                        if FAST_ROUTE:
                            self.gs_neighbour_matrix[nd.node.no].append(node.no)
                            self.gs_distance[nd.node.no][node.no] = delay
                        else:
                            self.neighbour_matrix[nd.node.no].append(node.no)
                            self.distance[nd.node.no][node.no] = delay
                    node.update_delay(nd.node.name, delay)
                    if not FAST_ROUTE:
                        self.neighbour_matrix[node.no].append(nd.node.no)
                        self.distance[node.no][nd.node.no] = delay
        self.router = router(self.neighbour_matrix, self.distance)
        print(self.neighbour_matrix)
        # print(self.distance)

        self.router.cal_n()
        # print("===========theory delay===========")
        # for row in self.distance:
        #     print(row)
        self.set_all_router()

    def load_hosts_instance(self):
        hosts_file = "hosts.json"
        with open(hosts_file, "r") as f:
            hosts = json.load(f)
        for host_name, host_details in hosts.items():
            HOST_INSTANCE_DICT[host_name] = Host(
                host_details["ip"],
                host_details["port"],
                host_details["username"],
                host_details["password"],
            )
            print("connect to", host_name)
            HOST_NAME_FROM_IP[host_details["ip"]] = host_name
            if not DEBUG:
                HOST_INSTANCE_DICT[host_name].connect()

    @staticmethod
    def load_tle(url):
        """
        description: 从tle文件获取整体卫星运行数据
        :param url: tle文件的url
        :return: tle中包含的所有卫星的列表
        """
        satellites = load.tle_file(url)
        return satellites

    @staticmethod
    def create_gs(positions):
        """
        description: 创建地面站
        :param positions: 地面站经纬度的二维列表，由多个一维列表组成，列表中第一个元素是纬度，第二个元素是经度
        :return: 用wgs84.latlon()构建的地面站列表
        """
        gss = []
        for position in positions:
            gs = wgs84.latlon(
                latitude_degrees=position[0],
                longitude_degrees=position[1],
                elevation_m=0,
            )
            gss.append(gs)
        return gss

    def set_all_router(self):
        for i in self.node_num_dict:
            # print(i)
            self.set_node_router(self.node_dict.get(self.node_num_dict.get(i).name))

    def set_node_router(self, node):
        if not node:
            print("error! The input satellite is not existed!")
        else:
            pre = self.router.get_next_src(node.no)
            # print(pre)
            node.set_pre(pre)

    def get_satellite_info(self, t, num=None, name=None):
        """
        description: 获取某颗卫星信息
        :param t: 时间
        :param num: 某颗卫星的编号
        :param name: 某颗卫星的名字
        :return: 信息字典
        """
        if num is not None:
            sat = self.satellites_num_dict[num]
        elif name is not None:
            sat = self.satellites_name_dict[name]
        else:
            return None
        info = {
            "name": sat.name,
            "inclination": sat.model.inclo,
            "sat_num": sat.model.satnum,
            "orbit_period": 1.0 / sat.model.no,
            "mean_motion": sat.model.no,
            "position": sat.at(t).position.km,
            "v": sat.at(t).velocity.km_per_s,
        }
        return info

    def get_all_satellites_info(self, t):
        """
        获取全部卫星信息
        :param t: 时间
        :return: 所有卫星的信息列表
        """
        infos = []
        for sat in self.satellites:
            info = {
                "name": sat.name,
                "inclination": sat.model.inclo,
                "sat_num": sat.model.satnum,
                "orbit_period": 1.0 / sat.model.no,
                "mean_motion": sat.model.no,
                "position": sat.at(t).position.km,
                "v": sat.at(t).velocity.km_per_s,
                "sat": sat,
            }
            infos.append(info)
        return infos

    def get_distance_2satellites(self, sat1_name, sat2_name, t):
        """
        description: 获取两颗卫星之间距离
        :param sat1_name: 卫星1名字
        :param sat2_name: 卫星2名字
        :param t: 时间
        :return: 两颗卫星之间距离
        """
        sat1 = self.satellites_name_dict[sat1_name]
        sat2 = self.satellites_name_dict[sat2_name]
        position_sat1 = sat1.at(t)
        position_sat2 = sat2.at(t)
        # distance = (position_sat1 - position_sat2).km
        R = position_sat1.distance().km
        distance = (
                position_sat1.separation_from(position_sat2).radians * R
        )  # calculate by radians, may not be correct when degree is large
        distance_abs = abs(distance)

        return distance_abs

    def get_interlink_delay(self, sat1_name, sat2_name, t):
        distance = self.get_distance_2satellites(sat1_name, sat2_name, t)
        # print("distance is", distance)
        light_vel = 3e5
        return int(distance / light_vel * 1000)

    def get_distance_sat_gs(self, sat_name, gs, t):
        sat = self.satellites_name_dict[sat_name]
        difference = sat - gs.loc
        difference = difference.at(t)
        _, _, distance = difference.altaz()
        return distance.km

    def get_sat_earth_link_delay(self, sat_name, gs, t):
        distance = self.get_distance_sat_gs(sat_name, gs, t)
        # print("distance gs", distance)
        light_vel = 3e5
        return int(distance / light_vel * 1000)

    def get_neighbour_satellite(self, name):
        """
        获取四颗相邻卫星名
        :param name: 查询卫星名
        :return: 相邻卫星名列表
        """
        result = {"up": None, "down": None, "left": None, "right": None}

        # 获取当前卫星轨道编号和index
        index = self.get_orbit(name)
        if index[0] < 0:
            print("no satellite")
            return
        up_index = (
            [index[0], index[1] - 1]
            if index[1] - 1 >= 0
            else [index[0], self.satellite_num_orbit - 1]
        )
        down_index = (
            [index[0], index[1] + 1]
            if index[1] + 1 < self.satellite_num_orbit
            else [index[0], 0]
        )
        left_index = (
            [index[0] - 1, index[1]]
            if index[0] - 1 >= 0
            else [self.orbit_num - 1, index[1]]
        )
        right_index = (
            [index[0] + 1, index[1]] if index[0] + 1 < self.orbit_num else [0, index[1]]
        )
        result["up"] = self.orbit_satellite[up_index[0]][up_index[1]]
        result["down"] = self.orbit_satellite[down_index[0]][down_index[1]]
        result["left"] = self.orbit_satellite[left_index[0]][left_index[1]]

        result["right"] = self.orbit_satellite[right_index[0]][right_index[1]]

        if self.from_real:
            # 同轨道卫星距离计算
            ts = load.timescale()
            t = ts.utc(2023, 10, 11)
            distance_same_orbit = {}
            for sat in self.orbit_satellite[index[0]]:
                if sat == name:
                    continue
                distance_same_orbit[sat] = self.get_distance_2satellites(name, sat, t)
            sorted_distance_same_orbit = sorted(
                distance_same_orbit.items(), key=lambda x: x[1]
            )

            # 前后两颗卫星名添加至结果，不严谨
            result["up"] = sorted_distance_same_orbit[0][0]
            result["down"] = sorted_distance_same_orbit[1][0]

            # 获取相邻轨道index
            neighbour_orbits = [index[0] - 1, index[0] + 1]
            if index[0] == 0:
                neighbour_orbits[0] = self.orbit_num - 1
            elif index[0] == self.orbit_num - 1:
                neighbour_orbits[1] = 0

            # 使用距离计算不同轨道的相邻卫星
            left_right = ["left", "right"]
            for i in range(2):
                distance_orbit = {}
                for sat in self.orbit_satellite[neighbour_orbits[i]]:
                    distance_orbit[sat] = self.get_distance_2satellites(name, sat, t)
                sorted_distance_orbit = sorted(
                    distance_orbit.items(), key=lambda x: x[1]
                )
                result[left_right[i]] = sorted_distance_orbit[0][0]

        return [result["up"], result["down"], result["left"], result["right"]]

    def update_node_neighbor(self, sat_name, t):
        """
        更新当前卫星节点的邻居信息，即更新地面站与卫星节点的连接关系,只更新节点间的时延配置等，不修改路由计算相关
        :param sat_name:
        :param t:
        :return:
        """
        print("Update node neighbor", sat_name)
        node = self.node_dict.get(sat_name)
        if not node:
            print("error! The input satellite name is not existed!")
        gs_list = self.get_connect_gs(sat_name, t)  # 获取当前卫星可以连接到的地面站列表
        gs_name_list = [node.name for node in gs_list]  # 卫星可连接的地面站名列表
        del_node_list = []
        already_in_gs_name = []
        add_node_list = []

        for neighbor in node.neighbor:
            # print(neighbor)
            if node.neighbor[neighbor].type == NodeType.Ground:
                # 邻居节点类型为地面站
                # 如果邻居节点不在卫星可连接的地面站列表中，则加入删除列表
                # 不然，需要更新延迟
                # 注意，双向延迟均需要更新
                if neighbor not in gs_name_list:
                    del_node_list.append(neighbor)
                else:
                    gs_new = None
                    for gs_ in gs_list:
                        if gs_.name == neighbor:
                            gs_new = gs_
                            already_in_gs_name.append(gs_.name)
                    delay = self.get_sat_earth_link_delay(sat_name, gs_new, t)
                    # gs_list.pop(gs_new.name)
                    node.update_delay(neighbor, delay)
                    self.node_dict.get(neighbor).update_delay(sat_name, delay)
            else:
                delay = self.get_interlink_delay(sat_name, neighbor, t)
                node.update_delay(neighbor, delay)
                neighborNode = self.node_dict.get(neighbor)
                self.distance[node.no][neighborNode.no] = delay

        for del_node in del_node_list:
            print("del", del_node, "from", node.name)
            node.del_neighbor(del_node)
            print("del", node.name, "from", del_node)
            self.node_dict.get(del_node).del_neighbor(node.name)

        for gs in gs_list:
            if gs.name not in already_in_gs_name:
                add_node_list.append(gs)

        for gs in add_node_list:
            print("node", node.name, "add", gs.name)
            node.add_neighbor(self.node_dict[gs.name])
            self.node_dict[gs.name].add_neighbor(node)
            delay = self.get_sat_earth_link_delay(sat_name, gs, t)
            node.update_delay(gs.name, delay)
            self.node_dict.get(gs.name).update_delay(sat_name, delay)

        node.set_delay_all()
        return

    def get_connect_gs(self, name, t):
        """
        获取卫星可以连接到的地面站列表
        :param t: load.timescale().utc(xxx)
        :param name: 卫星名
        :return: 地面站列表
        """
        gss_connected = []
        for gs in self.gs_list:
            if self.is_connect_gs(name, gs, t):
                gss_connected.append(gs)

        return gss_connected

    def is_connect_gs(self, name, gs, t):
        """
        检查卫星是否连接到地面站
        :param name: 卫星名
        :param gs: 地面站
        :param t: 时间
        :return: 卫星是否可以链接到当前地面站
        """
        sat = self.satellites_name_dict[name]
        difference = sat - gs.loc
        alt_degree, _, _ = difference.at(t).altaz()
        if float(alt_degree.degrees) >= -40:
            return True
        else:
            return False

    # def is_connect_gs(self, name, gs, t):
    #     """
    #     检查卫星是否连接到地面站
    #     :param name: 卫星名
    #     :param gs: 地面站
    #     :param t: 时间
    #     :return: 卫星是否可以链接到当前地面站
    #     """
    #     sat = self.satellites_name_dict[name]
    #     difference = sat - gs
    #     alt_degree = gs.at(t).separation_from(sat.at(t)).degrees
    #     # alt_degree, _, _ = difference.at(t).altaz()
    #     if abs(alt_degree) < 5.2:  # 根据三角关系计算 地球半径6370km,轨道高度550km，最小仰角40°
    #         return True
    #     else:
    #         return False

    def get_orbit(self, name):
        """
        获取卫星轨道编号和在轨道中的index
        :param name: 卫星名
        :return: 卫星轨道编号, 卫星在轨道中的index
        """
        index = -1, -1
        flag = False
        for orbit_ind in range(self.orbit_num):
            sat_ind = 0
            for sat in self.orbit_satellite[orbit_ind]:
                if name == sat:
                    index = orbit_ind, sat_ind
                    flag = True
                    break
                else:
                    sat_ind += 1
            if flag:
                break
        return index

    def get_satellite_num(self, ind):
        """
        获取某一轨道的卫星数量
        :param ind: 轨道编号
        :return: 轨道卫星数量
        """
        return len(self.orbit_satellite[ind])

    def get_position(self, name, t):
        """
        获取卫星位置
        :param name: 卫星名
        :param t: 当前时间
        :return: [x, y, z]位置坐标，以地心为中心
        """
        return self.satellites_name_dict[name].at(t).position.km

    # 整理所有轨道
    def clean_orbits(self, t):
        """
        轨道高度 + 轨道倾角 + 升交点的赤经
        二维列表[[卫星1名，卫星2名...]=>一个轨道, [卫星1名]]
        :return: None
        """
        focus_satellites = []
        focus_sat_dict = {}
        for sat in self.satellites:
            geocentric = sat.at(t)
            if self.from_real:
                height = wgs84.height_of(geocentric).km
                incli = sat.model.inclo * 180 / math.pi
                if height < 490 or incli < 53.15 or incli > 53.22:
                    continue
            focus_satellites.append(sat)
            focus_sat_dict[sat.name] = sat.model.nodeo * 180 / math.pi

        # 卫星按照升交点赤经排序
        sorted_focus_satellites = sorted(focus_sat_dict.items(), key=lambda x: x[1])

        clean_satellites = []
        current_degree = 0
        current_list = []
        for sat in sorted_focus_satellites:
            degree = sat[1]
            name = sat[0]
            if degree - current_degree < 2:
                current_list.append(name)
            else:
                clean_satellites.append(current_list)
                current_list = [name]
            current_degree = degree
        if self.from_real:
            for name in clean_satellites[0]:
                current_list.append(name)
            clean_satellites.append(current_list)
            clean_satellites.pop(0)
        else:
            clean_satellites.append(current_list)

        self.orbit_satellite = clean_satellites
        self.orbit_num = len(self.orbit_satellite)
        self.satellite_num_orbit = len(self.orbit_satellite[0])
        return

    # @staticmethod
    # def create_links(self,name1,name2):
    #

    # def create_all_containers(self):
    #     for sat in self.satellites:
    #         DockerInterface.create_container(sat.name, "gnb_ntn3")
    #         container_dict[sat.name] = Container(sat.name)
    #     for i, gs in enumerate(self.gs_list):
    #         if gs.typ == "ue":
    #             DockerInterface.create_container(gs.name, "firefox-ue")
    #             container_dict[gs.name] = Container(gs.name)
    #         else:
    #             DockerInterface.create_container(gs.name, gs.typ + "_ntn3")
    #             container_dict[gs.name] = Container(gs.name)

    #     ## create links
    #     for sat in self.satellites:
    #         neighbours = self.get_neighbour_satellite(sat.name)
    #         DockerInterface.create_bridge("b" + sat.name, "127.0.0.1")
    #         DockerInterface.connect_bridge("b" + sat.name, sat.name)
    #         DockerInterface.connect_bridge("b" + sat.name, neighbours[0])
    #         DockerInterface.connect_bridge("b" + sat.name, neighbours[2])
    #         gs_list = self.get_connect_gs(sat.name)
    #         for gs in gs_list:
    #             DockerInterface.connect_bridge("b" + sat.name, gs.name)

    def remove(self):
        pass

    def set_routes(self):
        for gs in self.gs_list:
            print(gs.name)

    def run(self):
        current_real_time_init = time.time()
        elapsed_real_time_init = current_real_time_init - self.sim_start_time
        simulated_time_init = (
                self.sim_start_time + elapsed_real_time_init * self.time_acceleration
        )
        utc_time_init = datetime.utcfromtimestamp(simulated_time_init).replace(
            tzinfo=timezone.utc
        )
        ts_init = load.timescale()
        t_init = ts_init.utc(utc_time_init)
        for sat in self.satellites:
            self.update_node_neighbor(sat.name, t_init)
        while True:
            current_real_time = time.time()
            elapsed_real_time = current_real_time - self.sim_start_time
            simulated_time = (
                    self.sim_start_time + elapsed_real_time * self.time_acceleration
            )
            utc_time = datetime.utcfromtimestamp(simulated_time).replace(
                tzinfo=timezone.utc
            )
            ts = load.timescale()
            t = ts.utc(utc_time)
            test_t = time.time()

            print("current time is", test_t)

            for sat in self.satellites:
                self.update_node_neighbor(sat.name, t)

            for gs in self.gs_list:
                self.node_dict.get(gs.name).set_delay_all()

            # print("===========theory delay===========")
            # for row in self.distance:
            #     print(row)
            print("===========real delay===========")
            if not DEBUG:
                all_ping_delay = self.get_all_ping_delay()
                for row in all_ping_delay:
                    print(row)

            # print(time.time() - test_t)
            self.renew_delay_update_all_route(t)
            self.set_all_router()
            print(time.time() - current_real_time)
            stop_time = 10
            if time.time() - current_real_time < stop_time:
                time.sleep(stop_time - (time.time() - current_real_time))
            # time.sleep(10 - (time.time() - current_real_time))
            # core = None
            # for gs in self.gs_list:
            #     if gs.name == "GroundStation-core0":
            #         core = gs
            # for sat in self.satellites:
            #     if self.is_connect_gs(sat.name, core, t):
            #         print("{}".format(sat.name), end=" ")
            # print("\n")
            # print(self.node_dict["GroundStation-core0"].neighbor)

    def load_containers(self, config_file="hosts.json"):

        json1 = json.load(open(config_file, "r"))

        for sat in self.satellites:
            # DockerInterface.create_container(sat.name, "gnb_ntn3")
            info = json1.get(sat.name)
            if info is None:
                CONTAINER_DICT[sat.name] = Container(sat.name, False, -1)
            else:
                CONTAINER_DICT[sat.name] = Container(
                    sat.name,
                    True,
                    ip=info["ip"],
                    port=info["if_port"],
                    ip_host=json1.get(info["host"])["ip"],
                    mac=info["mac"],
                    port_out=1,
                )
                # print(info[5])
                self.node_dict[sat.name].interfaceName = info["nic_name"]
        for gs in self.gs_list:
            print(gs.name)
            info = json1.get(gs.name)

            if info is None:
                CONTAINER_DICT[gs.name] = Container(gs.name, False, -1)
            else:
                CONTAINER_DICT[gs.name] = Container(
                    sat.name,
                    True,
                    ip=info["ip"],
                    port=info["if_port"],
                    ip_host=json1.get(info["host"])["ip"],
                    mac=info["mac"],
                    port_out=1,
                )
                self.node_dict.get(gs.name).interfaceName = info["nic_name"]

    def get_all_ping_delay(self):
        node_num = len(self.node_num_dict)
        ping_delay_matrix = [[0 for i in range(node_num)] for j in range(node_num)]
        for nos, nodes in self.node_num_dict.items():
            for nod, noded in self.node_num_dict.items():
                if nos == nod:
                    continue
                ping_delay_matrix[nos][nod] = nodes.get_ping_delay(noded)
        return ping_delay_matrix


if __name__ == "__main__":
    stations_url = (
        "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
    )
    local_ip = "127.0.0.1"
    # The first element in gs_position list is the location of core network,
    # the following elements are the location of ue
    flag = 1
    if flag:

        station_loc = [
            [20, 20],
            [30, 30],
            # [40, 40],
            # [45, 45],
            # [60, 60]
        ]
        system = SatelliteSystem(stations_url, station_loc, 0)
    # system.remove()
    else:
        sat_name = "starlink"
        core_name = "GroundStation-core0"
        ue_name = "GroundStation-ue"

        # for i in range(1, 10):
        #     DockerInterface.remove_container(sat_name + str(i))
        # DockerInterface.remove_container(core_name)
        # for i in range(4):
        #     DockerInterface.remove_container(ue_name + str(i + 1))
        # for i in range(1, 10):
        #     DockerInterface.remove_bridge("b" + sat_name + str(i))
        # DockerInterface.remove_bridge("b" + core_name)
        # for i in range(4):
        #     DockerInterface.remove_bridge("b" + ue_name + str(i + 1))

    # system.create_all_containers()
    # print(system.satellites[0])
    # print(system.get_neighbour_satellite(system.satellites[0].name))
