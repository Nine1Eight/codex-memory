#!/usr/bin/env python3
import cv2
import numpy as np

CHAIN = """
ka0-la0-ku0-ta0-pa0-ri0-de0-di0-ma0-bu0-ru0-be0-si0
la1-ku1-ta1-pa1-ri1-de1-di1-ma1-bu1-ru1-be1-si1
la2-ku2-ta2-pa2-ri2-de2-di2-ma2-bu2-ru2-be2-si2
la3-ku3-ta3-pa3-ri3
ka0-be-pa3-bu-ri3-bu-ru9-ma-bu7-di-ri4-la-bu2
""".replace("\n","-").split("-")

W, H = 2200, 800
img = np.zeros((H, W, 3), dtype=np.uint8)

def parse(t):
    base = ''.join([c for c in t if not c.isdigit()])
    num  = int(''.join([c for c in t if c.isdigit()] or "0"))
    return base, num

def draw(x,y,base,n):
    size = 18 + n*4
    color = (0, 255 - n*10, 150 + n*10)

    if base=="ka":
        cv2.rectangle(img,(x-size,y-size),(x+size,y+size),color,-1)
    elif base=="pa":
        pts=np.array([[x,y-size],[x-size,y+size],[x+size,y+size]])
        cv2.fillPoly(img,[pts],color)
    elif base=="da":
        pts=np.array([[x,y-size],[x-size,y],[x,y+size],[x+size,y]])
        cv2.fillPoly(img,[pts],color)
    elif base=="ri":
        cv2.circle(img,(x,y),size,color,-1)
    else:
        cv2.circle(img,(x,y),size//2,color,-1)

    cv2.putText(img,f"{base}{n}",(x-20,y+40),
        cv2.FONT_HERSHEY_SIMPLEX,0.4,(255,255,255),1)

x,y = 60,120

for i,t in enumerate(CHAIN):
    if i % 18 == 0 and i != 0:
        y += 140
        x = 60

    b,n = parse(t)
    draw(x,y,b,n)
    x += 110

cv2.imwrite("universal_bootstrap.png",img)
print("WROTE universal_bootstrap.png")
