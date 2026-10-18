using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace TechLounge {
static class PopupDpi {
    [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")] static extern IntPtr MonitorFromPoint(Point point,uint flags);
    [DllImport("shcore.dll")] static extern int GetDpiForMonitor(IntPtr monitor,int kind,out uint x,out uint y);
    internal static void Enable(){SetProcessDpiAwarenessContext(new IntPtr(-4));}
    internal static float PointerScale(){
        uint x,y;
        return GetDpiForMonitor(MonitorFromPoint(Cursor.Position,2),0,out x,out y)==0?x/96f:1f;
    }
}
}
