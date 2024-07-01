distance = [[0 for i in range(11)] for j in range(11)]

index = 1
with open("bbb.txt", "r") as f:
    for row in f:
        if "distance" in row:
            for i in range(11):
                row = f.readline().strip().strip("[]").split(", ")
                for j in range(11):
                    distance[i][j] = float(row[j])
            print("distance", index)
            index += 1
            for i in range(11):
                for j in range(11):
                    if distance[i][j] != distance[j][i]:
                        print(i, j, distance[i][j], distance[j][i])

# (GEMINI) PS C:\Users\Aether\Desktop\Gemini> python .\test02.py
# distance 1
# distance 2     
# 1 6 143.0 120.0
# 4 8 144.0 148.0
# 6 1 120.0 143.0
# 8 4 148.0 144.0
# distance 3
# distance 4
# 1 6 141.0 130.0
# 5 6 148.0 137.0
# 6 1 130.0 141.0
# 6 5 137.0 148.0
# distance 5
# distance 6