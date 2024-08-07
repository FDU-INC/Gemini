import paramiko


class Host:
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    def connect(self):

        self.client.connect(self.hostname, port=self.port, username=self.username, password=self.password)

    def close(self):
        self.client.close()

    def execute(self, command):
        # print(self.hostname,command)
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode('utf-8')

