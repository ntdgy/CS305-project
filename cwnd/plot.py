from datetime import datetime
import matplotlib.pyplot as plt

with open("sender2.log", 'r') as f:
    lines = f.readlines()

cwnd = []  # cwnd size time.time()

for line in lines:
    if line.startswith("cwnd"):
        cwnd_line = line.split()
        cwnd.append([cwnd_line[1], cwnd_line[2]])

# 画出 cwnd 横坐标为时间，纵坐标为 cwnd 大小
plt.figure()
print(cwnd)
start = float(cwnd[0][1])
x = [float(i[1]) - start for i in cwnd]
y = [float(i[0])/1300 for i in cwnd]
plt.plot(x, y)
plt.xlabel("Time Since Start (ms)")
plt.ylabel("cwnd")
plt.savefig("cwnd2.png")


