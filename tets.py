import os
with open('test.txt','wb') as f:
    # write 10 mb chunk of data
    f.write(os.urandom(10*1024*1024))

with open('test.txt','rb') as f:
    # read 10 mb chunk of data
    data = f.read(10*1024*1024)
    print(len(data))
    print(data[:1024])