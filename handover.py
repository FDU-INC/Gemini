from host import Host
import time

class Handover:
    def __init__(self, source_gnb_ip, target_gnb_ip, ue_ip):
        self.source_gnb_ip=source_gnb_ip
        self.target_gnb_ip=target_gnb_ip
        self.ue_ip=ue_ip
    def handover(self):
        source_gnb=Host(self.source_gnb_ip, 22, "root", "123")
        target_gnb=Host(self.target_gnb_ip, 22, "root", "123")
        ue=Host(self.ue_ip, 22, "root", "123")

        source_gnb.connect()
        target_gnb.connect()
        ue.connect()
        
        path="/root/new_gnb/UERANSIM_beforehandHO-main/"
        
        source_gnb_name=source_gnb.execute(path + "build/nr-cli --dump")
        target_gnb_name=target_gnb.execute(path + "build/nr-cli --dump")
        ue_name=ue.execute(path + "build/nr-cli --dump")

        # channel_source_gnb=source_gnb.invoke()
        # channel_target_gnb=target_gnb.invoke()
        # channel_ue=ue.invoke()
        source_gnb.execute(path+"build/nr-cli "+source_gnb_name+" --exec 'xnap-setup --ip "+self.target_gnb_ip+" --port 1478'\n")
        target_gnb.execute(path+"build/nr-cli "+target_gnb_name+" --exec 'xnap-setup --ip "+self.source_gnb_ip+" --port 1478'\n")
        ue.execute(path+"build/nr-cli "+ue_name+" --exec 'handover'\n")

        source_gnb.close()
        target_gnb.close()
        ue.close()
