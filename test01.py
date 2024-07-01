distance = [[0 for i in range(11)] for j in range(11)]
real = [[0 for i in range(11)] for j in range(11)]
delta = [[0 for i in range(11)] for j in range(11)]

sum_delta = 0

with open("bbb.txt", "r") as f:
    for row in f:
        if "distance" in row:
            for i in range(11):
                row = f.readline().strip().strip("[]").split(", ")
                for j in range(11):
                    distance[i][j] = float(row[j])
        elif "real delay" in row:
            print("===delta===")
            max_delta = 0
            for i in range(11):
                row = f.readline().strip().strip("[]").split(", ")
                for j in range(11):
                    real[i][j] = float(row[j])
                    delta[i][j] = round(real[i][j] / 2 - distance[i][j], 2)
                    sum_delta += delta[i][j]
                    max_delta = (
                        max_delta if max_delta >= abs(delta[i][j]) else abs(delta[i][j])
                    )
                    print("%5.2f" % delta[i][j], end="\t")
                print()
            print("max_delta: ", max_delta)
            average_delta = round(sum_delta / 121, 2)
            print("average_delta:", average_delta)
