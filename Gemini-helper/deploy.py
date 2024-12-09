import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)

sys.path.insert(0, parent_dir)
from host import Host
import time

class Deploy:
    def __init__(self, ip, ip_list):
        self.ip=ip
        self.ip_list=ip_list
    def execute(self):
        
        resource=Host(self.ip, 22, "root", "123")
        
        resource.connect()
        # Path to the file containing SSH commands
        command_file = 'sshCommand.txt'

        try:
            # Read the command file
            with open(command_file, 'r',encoding='utf-8') as file:
                for line in file:
                    if line:  # Ensure the line is not empty
                        if "#" in line:
                            if "resource build successfully" in line:
                                print(line)
                                break
                            continue
                        try:
                            print(line+"&&&&&&&::"+resource.execute(line))
                        except Exception as e:
                            print(f"Error executing command: {e}")
                        
        except FileNotFoundError:
            print(f"The command file {command_file} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    deploy=Deploy("10.177.47.58",[])
    deploy.execute()