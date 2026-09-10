"""Host-painted owned covers; never create children in a foreign DPI process."""
import ctypes
from ctypes import wintypes as w

class CaptionCovers:
    def __init__(self, user, parent, colour=0x15110F):
        self.user=user;self.parent=parent;self.handles=[]
        self.gdi=ctypes.WinDLL('gdi32');self.kernel=ctypes.WinDLL('kernel32')
        self.gdi.CreateSolidBrush.argtypes=[w.DWORD];self.gdi.CreateSolidBrush.restype=w.HBRUSH
        self.gdi.DeleteObject.argtypes=[w.HANDLE]
        self.kernel.GetModuleHandleW.argtypes=[w.LPCWSTR];self.kernel.GetModuleHandleW.restype=w.HMODULE
        callback=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
        user.DefWindowProcW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];user.DefWindowProcW.restype=ctypes.c_ssize_t
        self.proc=callback(lambda hwnd,msg,wp,lp:user.DefWindowProcW(hwnd,msg,wp,lp))
        class Class(ctypes.Structure):
            _fields_=[('style',w.UINT),('proc',callback),('cls',ctypes.c_int),('win',ctypes.c_int),('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),('brush',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]
        self.instance=self.kernel.GetModuleHandleW(None)
        self.name='TL_Caption_'+str(parent)
        self.brush=self.gdi.CreateSolidBrush(colour)
        definition=Class(0,self.proc,0,0,self.instance,None,None,self.brush,None,self.name)
        user.RegisterClassW.argtypes=[ctypes.POINTER(Class)]
        user.UnregisterClassW.argtypes=[w.LPCWSTR,w.HINSTANCE]
        if not user.RegisterClassW(ctypes.byref(definition)): raise ctypes.WinError()
        user.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,ctypes.c_void_p]
        user.CreateWindowExW.restype=w.HWND
        user.DestroyWindow.argtypes=[w.HWND]
        user.GetClientRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
        for _ in range(2):
            # Cross-process child windows can reset the publisher's DPI context
            # and its compositor can paint over them. Owned popups avoid both.
            hwnd=user.CreateWindowExW(0x08000080,self.name,'',0x80000000,0,0,1,1,parent,None,self.instance,None)
            if not hwnd: self.close();raise ctypes.WinError()
            self.handles.append(hwnd)
        self.last=None

    def update(self, tool_region=None, crop_signature=None):
        rect=w.RECT();self.user.GetClientRect(self.parent,ctypes.byref(rect))
        origin=w.POINT();self.user.ClientToScreen(self.parent,ctypes.byref(origin))
        outer=w.RECT();self.user.GetWindowRect(self.parent,ctypes.byref(outer))
        scale=(self.user.GetDpiForWindow(self.parent) or 96)/96
        geometry=[(origin.x,origin.y,round(220*scale),round(36*scale)),(origin.x+rect.right-round(138*scale),origin.y,round(138*scale),round(36*scale))]
        visible=self.user.IsWindowVisible(self.parent) and not self.user.IsIconic(self.parent)
        signature=(geometry,visible,crop_signature)
        if signature==self.last:return
        self.gdi.CreateRectRgn.argtypes=[ctypes.c_int]*4;self.gdi.CreateRectRgn.restype=w.HANDLE
        self.gdi.CombineRgn.argtypes=[w.HANDLE,w.HANDLE,w.HANDLE,ctypes.c_int]
        self.gdi.OffsetRgn.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_int]
        for hwnd,bounds in zip(self.handles,geometry):
            # Copy the parent's rounded outline and shell-popup exclusions.
            if tool_region:
                region=self.gdi.CreateRectRgn(0,0,0,0)
                self.gdi.CombineRgn(region,tool_region,tool_region,5)
                self.gdi.OffsetRgn(region,outer.left-bounds[0],outer.top-bounds[1])
                limit=self.gdi.CreateRectRgn(0,0,bounds[2],bounds[3])
                self.gdi.CombineRgn(region,region,limit,1)
                self.gdi.DeleteObject(limit)
                if not self.user.SetWindowRgn(hwnd,region,True):self.gdi.DeleteObject(region)
            self.user.SetWindowPos(hwnd,0,*bounds,0x0210 | (0x40 if visible else 0x80))
        self.last=signature

    def close(self):
        for hwnd in self.handles:
            if self.user.IsWindow(hwnd):self.user.DestroyWindow(hwnd)
        self.handles=[]
        self.user.UnregisterClassW(self.name,self.instance)
        self.gdi.DeleteObject(self.brush)
