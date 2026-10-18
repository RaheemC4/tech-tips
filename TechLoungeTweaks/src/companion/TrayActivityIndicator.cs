using System;using System.Diagnostics;using System.Drawing;using System.Drawing.Drawing2D;using System.Windows.Forms;
namespace TechLounge {
sealed class TrayActivityIndicator:Control {
    readonly Timer frames=new Timer{Interval=16};readonly Stopwatch clock=new Stopwatch();readonly Color tint;readonly bool animate;
    internal TrayActivityIndicator(Color tint){this.tint=tint;animate=PopupMotion.Enabled();AccessibleRole=AccessibleRole.StaticText;AccessibleName="Action in progress";TabStop=false;SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint,true);frames.Tick+=(s,e)=>{SyncAnimation();if(frames.Enabled)Invalidate();};}
    void SyncAnimation(){if(frames==null||IsDisposed)return;if(Visible&&animate){clock.Start();frames.Start();}else{frames.Stop();clock.Stop();}}
    protected override void OnVisibleChanged(EventArgs e){base.OnVisibleChanged(e);SyncAnimation();}
    protected override void OnPaint(PaintEventArgs e){
        // WM_SETREDRAW restores native visibility without OnVisibleChanged.
        SyncAnimation();
        var popup=FindForm() as Popup;if(popup==null)return;var offset=popup.PointToClient(PointToScreen(Point.Empty));popup.PaintBackdrop(e.Graphics,new Rectangle(-offset.X,-offset.Y,popup.Width,popup.Height));e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        float stroke=Math.Max(2,popup.Pixels(2));var ring=new RectangleF(stroke,stroke,Width-stroke*2,Height-stroke*2);
        using(var track=new Pen(Color.FromArgb(40,tint),stroke))e.Graphics.DrawEllipse(track,ring);
        double turns=clock.Elapsed.TotalMilliseconds/1400.0;float start=animate?(float)(turns*360):-90;float sweep=220;
        using(var pen=new Pen(tint,stroke)){pen.StartCap=pen.EndCap=LineCap.Round;e.Graphics.DrawArc(pen,ring,start,sweep);}
    }
    protected override void Dispose(bool disposing){if(disposing){frames.Stop();frames.Dispose();clock.Stop();}base.Dispose(disposing);}
}
}
