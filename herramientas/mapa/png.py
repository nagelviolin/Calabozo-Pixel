import zlib,struct,numpy as np
def save(path,img):
    h,w,_=img.shape; raw=b''.join(b'\x00'+img[y].astype(np.uint8).tobytes() for y in range(h))
    def ch(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b''))
