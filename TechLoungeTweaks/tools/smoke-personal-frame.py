"""Verify personal tool framing with disposable native windows, no tool execution."""
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tool_windows import FloatingTools,ToolSurface,WindowLink,inset_rect
u=FloatingTools._native()
u.SetThreadDpiAwarenessContext.argtypes=[ctypes.c_void_p]
u.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
u.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,ctypes.c_void_p]
u.CreateWindowExW.restype=w.HWND
u.DestroyWindow.argtypes=[w.HWND]
for key in ('driverbooster','treesize'):
    owner=u.CreateWindowExW(0,'STATIC','Host',0x00CF0000,-10000,-10000,1200,800,None,None,None,None)
    tool=u.CreateWindowExW(0,'STATIC','Tool',0x00CF0000,-10000,-10000,900,600,owner,None,None,None)
    surface=ToolSurface(u,tool,key,owner)
    link=WindowLink(u,owner,tool,surface=surface)
    try:
        link.start()
        for i in range(3):
            # Simulate a custom drag without move-start/end events and an owner reset.
            u.SetWindowLongPtrW(tool,-8,0)
            u.SetWindowPos(tool,None,-8500+i*10,-8800,700,500,0x0014)
            link.pump()
            expected=inset_rect(link.rect(owner),u.GetDpiForWindow(owner) or 96)
            x,y,width,height=expected
            assert link.rect(tool)==(x,y,x+width,y+height),(key,link.rect(tool),expected)
            assert u.GetWindowLongPtrW(tool,-8)==owner
        g=surface.gdi
        g.PtInRegion.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_int]
        region=g.CreateRectRgn(0,0,0,0)
        try:
            u.GetWindowRgn(tool,region)
            assert not g.PtInRegion(region,width-10,10),'Duplicate close button still exposed'
            assert g.PtInRegion(region,20,50),'Tool menu was clipped'
        finally:g.DeleteObject(region)
        print('PASS',key,'custom movement, owner restoration, caption exclusion and menu preservation')
    finally:
        link.close();surface.restore();u.DestroyWindow(tool);u.DestroyWindow(owner)
