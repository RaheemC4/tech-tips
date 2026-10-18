using System;using System.Runtime.InteropServices;using System.Windows.Forms;
namespace TechLounge {
// Windows otherwise copies old client pixels while resizing/moving native controls.
// https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowpos
static class TrayGeometry {
    [StructLayout(LayoutKind.Sequential)] internal struct WindowPosition {
        internal IntPtr Window,After;internal int X,Y,Width,Height;internal uint Flags;
    }
    internal static void DiscardCopiedPixels(ref Message message,bool movingChild){
        if(message.Msg!=0x46||message.LParam==IntPtr.Zero)return;
        var position=(WindowPosition)Marshal.PtrToStructure(message.LParam,typeof(WindowPosition));
        if(movingChild?(position.Flags&3)==3:(position.Flags&1)!=0)return;
        position.Flags|=0x100; // SWP_NOCOPYBITS: invalidate, do not save/copy old pixels.
        Marshal.StructureToPtr(position,message.LParam,false);
    }
}
}
