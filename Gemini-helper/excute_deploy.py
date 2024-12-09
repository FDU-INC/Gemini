import paramiko
import yaml
import json
import time


# config_file = 'config.yaml'


# with open(config_file, 'r') as file:
#     config = yaml.safe_load(file)
resource="http://10.177.47.172"

config={"hosts":[{"ip":"10.177.47.35","password":"123","virture":["node1","sat01","sat02","sat03","sat04","ue"]}]}

master_host_ip="10.177.47.35"

file_path = 'hosts.json'

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data

hosts_dict = read_json_file(file_path)
# ip_dict={name: data["ip"] for name, data in hosts_dict.items()} # for now there could be a little problem about the different name between json file and virtual-hostname
ip_dict={
    'host1': '10.177.47.59',
    'host2': '10.177.47.35',
    'master': '10.177.47.21',
    'node1': '10.177.47.22',
    'sat01': '10.177.47.11',
    'sat02': '10.177.47.12',
    'sat03': '10.177.47.13',
    'sat04': '10.177.47.14',
    'sat05': '10.177.47.15',
    'ue': '10.177.47.41'
}



class SSHClient:
    def __init__(self, ip, password, max_attempts=30, delay=20):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ip = ip
        self.password = password
        self.max_attempts = max_attempts
        self.delay = delay
        self.connected = False
        for attempt in range(self.max_attempts):
            try:
                self.ssh.connect(self.ip, username='root', password=self.password,timeout=600)
                self.connected = True
                print(f"Connected to {self.ip} on attempt {attempt + 1}")
                break
            except Exception as e:
                print(f"Connection failed on attempt {attempt + 1}: {e}")
                if attempt == self.max_attempts - 1:
                    print("Max connection attempts reached. Exiting program.")
                    exit(1)

        
        
    def connect(self,ip,password):
        self.ip=ip
        self.password=password
        for attempt in range(self.max_attempts):
            try:
                self.ssh.connect(self.ip, username='root', password=self.password,timeout=600)
                self.connected = True
                print(f"Connected to {self.ip} on attempt {attempt + 1}")
                break
            except Exception as e:
                print(f"Connection failed on attempt {attempt + 1}: {e}")
                if attempt == self.max_attempts - 1:
                    print("Max connection attempts reached. Exiting program.")
                    exit(1)

    def execute_command(self, command):
        stdin, stdout, stderr = self.ssh.exec_command(command)
        print(command+"&::"+stderr.read().decode())
        output=stdout.read().decode()
        print(command+"&:stdout:"+output)
        return output
    
    def execute_command2(self, command, timeout):
        stdin, stdout, stderr = self.ssh.exec_command(command,timeout=timeout)
        return stdout.read().decode()

    def close(self):
        self.ssh.close()


def create_vm(ssh_client, vm_name, xml_file):
    # ssh_client.execute_command(f"cp /var/lib/libvirt/xml-copy/{vm_name}.xml {xml_file}")
    # ssh_client.execute_command(f"cp /var/lib/libvirt/images/{vm_name} (copy).qcow2 /var/lib/libvirt/images/{vm_name}.qcow2")
    
    exist_cmd = f"virsh list --all | grep {vm_name}"
    output = ssh_client.execute_command(exist_cmd)
    if vm_name not in output:
        ssh_client.execute_command(f"wget {resource}/config_files/{vm_name}.xml -O {xml_file}")
        print("accquire the xml file")
        ssh_client.execute_command(f"wget {resource}/files/{vm_name}.qcow2 -O /var/lib/libvirt/images/{vm_name}.qcow2")
        print("accquire the files successfully")
        ssh_client.execute_command(f"virsh define {xml_file};")
        if vm_name=="master":
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ip=ip_dict[vm_name]
            print(f"start {vm_name}")
            for attempt in range(30):
                try:
                    print(f"Creating... Connected to {ip} on attempt {attempt + 1}")
                    ssh.connect(ip, username='root', password="123", timeout=10)
                    ssh.close()
                    break
                except Exception as e:
                    print(f"Connection failed on attempt {attempt + 1}")
                    if attempt == 29:
                        print("Max connection attempts reached. Exiting program.")
                        exit(1)
                
    else:
        print(f"{vm_name} already exists.")

def wait_for_vm_to_start(ssh_client, vm_name):
    wait_cmd = f"virsh wait {vm_name} --timeout 300 --running"
    ssh_client.execute_command(wait_cmd)
    print(f"{vm_name} is now running.")


def clone_vm(ssh_client, original_vm, new_vm_names, token):
    clone_cmd = "virt-clone"
    clone_list=[]
    for new_vm_name in new_vm_names:
        output = ssh_client.execute_command(f"virsh list --all | grep {new_vm_name}")
        if new_vm_name not in output:
            print(f"Cloning {original_vm} to {new_vm_name}...")
            print(ssh_client.execute_command(f"{clone_cmd} -o {original_vm} -n {new_vm_name} --auto-clone"))
            clone_list.append(new_vm_name)
    for new_vm_name in new_vm_names:
        output = ssh_client.execute_command(f"virsh list --all | grep {new_vm_name}")
        output2 = ssh_client.execute_command(f"virsh list | grep {new_vm_name}")
        if new_vm_name not in output2 and new_vm_name in output:
            if new_vm_name in clone_list:
                for attempt in range(30):
                    try:
                        start_cmd = f"virsh start {new_vm_name}"
                        ssh_client.execute_command(start_cmd)
                        print(f"Create {new_vm_name} on attempt {attempt + 1}")
                        break
                    except Exception as e:
                        print(f"Create failed on attempt {attempt + 1}: {e}")
                        time.sleep(10)
                        if attempt == 29:
                            print("Max connection attempts reached. Exiting program.")
                            exit(1)
                # Update netplan and hostname
                ip = ip_dict.get(new_vm_name)  
                ssh_client_virture=SSHClient(ip_dict[original_vm], "123")
                modify_config_file(ssh_client_virture, new_vm_name, ip)
                set_hostname(ssh_client_virture, new_vm_name, new_vm_name)
                ssh_client_virture.close()
                # Restart the VM to apply changes
                reboot_cmd = f"virsh reboot {new_vm_name}"
                ssh_client.execute_command(reboot_cmd)
                
                ssh_client_virture2=SSHClient(ip_dict[new_vm_name], "123")
                join_cmd = token
                ssh_client_virture2.execute_command(join_cmd)
                ssh_client_virture2.close()
            else:
                for attempt in range(30):
                    try:
                        start_cmd = f"virsh start {new_vm_name}"
                        ssh_client.execute_command(start_cmd)
                        print(f"Create {new_vm_name} on attempt {attempt + 1}")
                        break
                    except Exception as e:
                        print(f"Create failed on attempt {attempt + 1}: {e}")
                        time.sleep(10)
                        if attempt == 29:
                            print("Max connection attempts reached. Exiting program.")
                            exit(1)
                    
                ssh_client_virture2=SSHClient(ip_dict[new_vm_name], "123")
                join_cmd = token
                ssh_client_virture2.execute_command(join_cmd)
                ssh_client_virture2.close()
        else:
            ssh_client_virture2=SSHClient(ip_dict[new_vm_name], "123")
            join_cmd = token
            ssh_client_virture2.execute_command(join_cmd)
            ssh_client_virture2.close()


def modify_config_file(ssh_client, vm_name, ip):
    config_file_path = "/etc/netplan/00-installer-config.yaml"
    sed_cmd = f"sed -i 's/10.177.47.12/{ip}/g' {config_file_path}"
    ssh_client.execute_command(sed_cmd)
    print("modify_config_file_successfully")

    
def modify_gnb_config_file_start_gnb(ssh_client, vm_name, ip):
    
    config_file_path = "/root/new_gnb/UERANSIM_beforehandHO/config/open5gs-gnb.yaml;"
    if ip != "10.177.47.12":
        print("change gnb-config")
        sed_cmd = f"sed -i 's/10.177.47.12/{ip}/g' {config_file_path}"
        ssh_client.execute_command(sed_cmd)
    print("find if has already created a gnb")
    exist_gnb=ssh_client.execute_command(f"/root/new_gnb/UERANSIM_beforehandHO/build/nr-cli --dump")
    if exist_gnb == "":
        try:
            ssh_client.execute_command2(f"/root/new_gnb/UERANSIM_beforehandHO/build/nr-gnb -c /root/new_gnb/UERANSIM_beforehandHO/config/open5gs-gnb.yaml",5)
        except Exception as e:
            print(f"{ip}-gnb start")
    else:
        print("gnb exist")
    
def modify_ue_config_file_and_start_ue(ssh_client, vm_name, ip):
    config_file_path = "/root/new_gnb/UERANSIM_beforehandHO/config/open5gs-ue.yaml;"
    sed_cmd = f"sed -i 's/10.177.47.12/{ip}/g' {config_file_path}"
    ssh_client.execute_command(sed_cmd)
    exist_ue=ssh_client.execute_command(f"/root/new_gnb/UERANSIM_beforehandHO/build/nr-cli --dump")
    if exist_ue == "":
        try:
            ssh_client.execute_command2(f"/root/new_gnb/UERANSIM_beforehandHO/build/nr-ue -c /root/new_gnb/UERANSIM_beforehandHO/config/open5gs-ue.yaml",5)
        except Exception as e:
            print(f"{ip}-ue start")


def set_hostname(ssh_client, vm_name, new_hostname):
    hostname_cmd = f"hostnamectl set-hostname {new_hostname}"
    ssh_client.execute_command(hostname_cmd)


def main(config):
    token = ""
    master_host=SSHClient(master_host_ip, "123")
    create_vm(master_host, 'master', '/etc/libvirt/qemu/master.xml')
    
    master = SSHClient("10.177.47.21", "123")
    ssh_client = SSHClient("10.177.47.21", "123")
    base_virture=["master","sat01","sat02","node1"]
    master_init_cmd = "kubeadm reset --force;kubeadm init --kubernetes-version=v1.23.5 --pod-network-cidr=10.244.0.0/16 --image-repository registry.aliyuncs.com/google_containers --service-cidr=10.96.0.0/12 --apiserver-advertise-address=10.177.47.21;"
    result=master.execute_command(master_init_cmd)
    token="kubeadm reset --force;"+result.split('\n')[-3].split('\\')[0] + result.split('\n')[-2]
    print("token:"+token)
    
    master.execute_command(f"mkdir -p $HOME/.kube")
    print(1)
    master.execute_command(f"sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config")
    print(2)
    master.execute_command(f"sudo chown $(id -u):$(id -g) $HOME/.kube/config")
    
    print("init finish")
    for host in config['hosts']:
        ssh_client.connect(host['ip'], host['password'])
        #############################
        # used to code for delete the extra vms(not have to delete, could exchange to other type vm)
        
        
        
        
        
        #############################
        
        # Clone VMs based on the host configuration
        clean_virture=[element for element in host["virture"] if element not in base_virture]

        sat01_type_virture=[element for element in clean_virture if "sat01-" in element]
        sat02_type_virture=[element for element in clean_virture if ("sat" in element or "ue" in element) and "sat01-" not in element]
        node1_type_virture=[element for element in clean_virture if "node" in element]
        if sat01_type_virture!=[] or 'sat01' in host["virture"]:
            create_vm(ssh_client, 'sat01', '/etc/libvirt/qemu/sat01.xml')
            ssh_client.execute_command(f"virsh destroy sat01")
        if sat02_type_virture!=[] or 'sat02' in host["virture"]:
            create_vm(ssh_client, 'sat02', '/etc/libvirt/qemu/sat02.xml')
            ssh_client.execute_command(f"virsh destroy sat02")
        if node1_type_virture!=[] or 'node1' in host["virture"]:
            create_vm(ssh_client, 'node1', '/etc/libvirt/qemu/node1.xml')
            ssh_client.execute_command(f"virsh destroy node1")

        # Clone VMs based on the host configuration
        clean_virture=[element for element in host["virture"] if element not in base_virture]

        sat01_type_virture=[element for element in clean_virture if "sat01-" in element]
        sat02_type_virture=[element for element in clean_virture if ("sat" in element or "ue" in element) and "sat01-" not in element]
        node1_type_virture=[element for element in clean_virture if "node" in element]
        clone_vm(ssh_client, 'sat02', sat02_type_virture, token)
        clone_vm(ssh_client, 'sat01', sat01_type_virture, token)
        clone_vm(ssh_client, 'node1', node1_type_virture, token)

        # for vm in [f"sat0{i}" for i in range(3, 6)] + [f"sat01-{i}" for i in range(1, 6)] + [f"node1-{i}" for i in range(1, 6)]:
        #     join_cmd = token
        #     ssh_client.execute_command(join_cmd)

        ssh_client.close()
    
    ssh_client_each=SSHClient(master_host_ip,"123")
    for host in config['hosts']:
        ssh_client.connect(host['ip'], host['password'])
        for new_vm_name in base_virture:
            if new_vm_name == "master":
                continue
            if new_vm_name in host["virture"]:
                output2 = ssh_client.execute_command(f"virsh list | grep s{new_vm_name}")
                if new_vm_name not in output2:
                    start_cmd = f"virsh start {new_vm_name}"
                    ssh_client.execute_command(start_cmd)
                    ssh_client_each.connect(ip_dict[new_vm_name],"123")
                    join_cmd = token
                    ssh_client_each.execute_command(join_cmd)
                    ssh_client_each.close()
                else:
                    delete_cmd=f"virsh destroy {new_vm_name};virsh undefine {new_vm_name} --remove-all-storage"
                    ssh_client.execute_command(delete_cmd)
        
        # # danger code            
        # output=ssh_client.execute_command(f"virsh list --all")
        # vms = output.strip().split('\n')[2:]
        # vms_list = [vm.split()[1] for vm in vms] 
        # vms_to_keep = host["virture"]
        # for vm in vms_list:
        #     if vm not in vms_to_keep:
        #         print(f"Deleting VM: {vm}")
        #         ssh_client.execute_command(f"virsh destroy {vm};virsh undefine --remove-all {vm}")
               
        ssh_client.close()
    print("gnb-ue config start")
    for host in config['hosts']:
        for vm_name in host["virture"]:
            if "sat" in vm_name and "sat01" not in vm_name:
                ssh_client.connect(ip_dict[vm_name],"123")
                modify_gnb_config_file_start_gnb(ssh_client,vm_name,ip_dict[vm_name])
                ssh_client.close()
            if "ue" in vm_name:
                ssh_client.connect(ip_dict[vm_name],"123")
                modify_ue_config_file_and_start_ue(ssh_client, vm_name,ip_dict[vm_name])
                ssh_client.close()
                
    # Execute kubectl commands on the master node
    master_kubectl_cmds = [
        "kubectl taint nodes --all node-role.kubernetes.io/master-",
        "kubectl label nodes node1 mobile-core=cp",
        "kubectl label nodes sat01 mobile-core=up2"
    ]
    for cmd in master_kubectl_cmds:
        master.execute_command(cmd)

    # Deploy Open5GS on the master node
    open5gs_cmd = "kubectl apply -f /root/workspace/kube-flannel.yml; kubectl create namespace open5gs;"
    master.execute_command(open5gs_cmd)
    last_cmd="helm install open5gs -n open5gs /root/workspace/k8s-5g-core"
    master.execute_command(last_cmd)
    master.close()

if __name__ == "__main__":
    main(config)