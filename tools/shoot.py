#!/usr/bin/env python3
"""Capture the Mesen game window robustly: full-screen grab cropped to the
Mesen window's Quartz bounds. Usage: shoot.py <out.png>"""
import sys, subprocess, tempfile, os, Quartz
from PIL import Image

def mesen_bounds():
    wl = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID)
    best = None
    for w in wl:
        if 'Mesen' in str(w.get('kCGWindowOwnerName', '')):
            b = w['kCGWindowBounds']
            area = b['Width'] * b['Height']
            if best is None or area > best[0]:
                best = (area, b)
    return best[1] if best else None

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/mesen.png"
    b = mesen_bounds()
    if not b:
        print("no Mesen window"); sys.exit(1)
    main_disp = Quartz.CGMainDisplayID()
    pts_w = Quartz.CGDisplayBounds(main_disp).size.width
    tmp = tempfile.mktemp(suffix=".png")
    subprocess.run(["screencapture", "-x", tmp], check=True)
    img = Image.open(tmp)
    scale = img.width / pts_w
    x = int(b['X'] * scale); y = int(b['Y'] * scale)
    w = int(b['Width'] * scale); h = int(b['Height'] * scale)
    img.crop((x, y, x + w, y + h)).save(out)
    os.remove(tmp)
    print(f"{out} {int(b['X'])},{int(b['Y'])},{int(b['Width'])},{int(b['Height'])} scale={scale:.2f}")

if __name__ == "__main__":
    main()
