using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using Microsoft.Win32;
namespace TechLounge {
// A transparent idle glyph lets Explorer supply the actual taskbar surface.
static class TrayGlyph {
    [DllImport("user32.dll")] static extern bool DestroyIcon(IntPtr handle);
    public static Icon Create(Color accent,bool active,bool light) {
        using(var bitmap=new Bitmap(32,32)) {
            using(var g=Graphics.FromImage(bitmap)) {
                g.Clear(Color.Transparent);g.SmoothingMode=SmoothingMode.AntiAlias;
                if(active)using(var shape=Popup.Round(new Rectangle(0,0,31,31),7))using(var fill=new SolidBrush(accent))g.FillPath(fill,shape);
                using(var pen=new Pen(active||!light?Color.FromArgb(240,245,252):Color.FromArgb(40,48,60),2)) {
                    pen.StartCap=pen.EndCap=LineCap.Round;
                    for(int i=0;i<3;i++)g.DrawLine(pen,6,9+i*7,26,9+i*7);
                    pen.Width=4;
                    g.DrawLine(pen,11,6,11,12);g.DrawLine(pen,22,13,22,19);g.DrawLine(pen,14,20,14,26);
                }
            }
            IntPtr handle=bitmap.GetHicon();
            try {using(var borrowed=Icon.FromHandle(handle))return (Icon)borrowed.Clone();}
            finally {DestroyIcon(handle);}
        }
    }
    public static bool LightTaskbar() {
        using(var key=Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"))
            return key!=null && Convert.ToInt32(key.GetValue("SystemUsesLightTheme",0))!=0;
    }
}
}
