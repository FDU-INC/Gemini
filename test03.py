distance = [[0 for i in range(11)] for j in range(11)]

with open("bbb.txt", "r") as f:
    for row in f:
        if "neighbour_matrix" in row:
            for i in range(11):
                row = f.readline().strip().strip("[]").split(", ")
                for j in row:
                    distance[i][int(j)] = 1

for i in range(11):
    for j in range(11):
        if distance[i][j] != distance[j][i]:
            print(i, j)
# (GEMINI) PS C:\Users\Aether\Desktop\Gemini> python .\test01.py  > ccc.txt
# distance 1
# distance 2
# 1 5
# 5 1
# distance 3
# distance 4
# 2 3
# 3 2
