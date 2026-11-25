"""The Xbox controller's raw events for 60 s, straight from evdev (no duck code): which button and axis codes it sends, and whether the
Bluetooth link drops. For a new controller, or one that pairs but does nothing.   python padtest.py
"""
import os,struct,time,select,re
KEYS={304:"A",305:"B",307:"X",308:"Y",310:"LB",311:"RB",314:"View",315:"Menu",316:"Xbox",317:"LStick",318:"RStick",167:"Share",158:"View",172:"Xbox"}
ABS={0:"LX",1:"LY",2:"LT",3:"RX",4:"RY",5:"RT",9:"RT",10:"LT",16:"DpadX",17:"DpadY"}
def find():
    for blk in open("/proc/bus/input/devices").read().split("\n\n"):
        if "Xbox" in blk:
            m=re.search(r"(event\d+)",blk)
            if m: return "/dev/input/"+m.group(1)
last={};t0=time.time();n=0;fd=None;drops=0
print("press buttons now (60 s)",flush=True)
while time.time()-t0<60:
    t=time.time()-t0
    if fd is None:
        ev=find()
        if not ev: time.sleep(0.3); continue
        try: fd=os.open(ev,os.O_RDONLY|os.O_NONBLOCK); print(f"{t:5.1f}s connected {ev}",flush=True)
        except OSError: time.sleep(0.3); continue
    try:
        r,_,_=select.select([fd],[],[],0.5)
        if not r: continue
        data=os.read(fd,24*64)
    except OSError:
        print(f"{t:5.1f}s dropped",flush=True); drops+=1; os.close(fd); fd=None; continue
    for i in range(0,len(data),24):
        s,us,typ,code,val=struct.unpack("llHHi",data[i:i+24])
        if typ==1:
            print(f"{t:5.1f}s button {KEYS.get(code,code)} {'down' if val else 'up'}",flush=True); n+=1
        elif typ==3:
            name=ABS.get(code,code)
            if name not in last or abs(val-last[name])>8000 or str(name).startswith("Dpad"):
                last[name]=val; print(f"{t:5.1f}s axis {name} {val}",flush=True); n+=1
print("events shown:",n,"drops:",drops)
