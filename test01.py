import math

theory_delay = [[0 for i in range(11)] for j in range(11)]
real_delay = [[0 for i in range(11)] for j in range(11)]
delta_delay = [[0 for i in range(11)] for j in range(11)]

with open("ping_result1.txt", "r") as f:
    row1 = f.readline()
    i = 0
    j = 0
    for k in range(11):
        row = f.readline()
        row = row.strip().lstrip("[").rstrip("]").split(", ")
        for num in row:
            if num == "inf":
                theory_delay[i][j] = math.inf
            else:
                theory_delay[i][j] = float(num)
            j += 1
        i += 1
        j = 0

    row2 = f.readline()
    i = 0
    j = 0
    for k in range(11):
        row = f.readline()
        row = row.strip().lstrip("[").rstrip("]").split(", ")
        for num in row:
            if num == "inf":
                real_delay[i][j] = math.inf
            else:
                real_delay[i][j] = float(num) / 2
            j += 1
        i += 1
        j = 0


for i in range(11):
    for j in range(11):
        delta_delay[i][j] = real_delay[i][j] - theory_delay[i][j]
        print(round(delta_delay[i][j], 1), end="\t")
    print()


# 对称
# for i in range(11):
#     for j in range(11):
#         print(round(real_delay[i][j] - real_delay[j][i],1), end="\t")
