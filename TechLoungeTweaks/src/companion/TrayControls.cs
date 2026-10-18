using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;
namespace TechLounge {
// A clipped viewport with one slim scroll thumb, never native horizontal chrome.
sealed class TrayScrollPanel:Panel {
    int offset,maximum,dragY,dragOffset;bool moving,dragging;
    protected override void WndProc(ref Message message){TrayGeometry.DiscardCopiedPixels(ref message,true);base.WndProc(ref message);}
    public TrayScrollPanel(){AutoScroll=false;DoubleBuffered=true;SetStyle(ControlStyles.ResizeRedraw,true);}
    int P(int n){var popup=FindForm() as Popup;return popup==null?n:popup.Pixels(n);}
    public void ResetScroll(){ScrollTo(0);}
    protected override void OnLayout(LayoutEventArgs e){base.OnLayout(e);if(moving)return;int bottom=0;foreach(Control c in Controls)bottom=Math.Max(bottom,c.Bottom+offset);maximum=Math.Max(0,bottom-ClientSize.Height+P(4));if(offset>maximum)ScrollTo(maximum);Invalidate();}
    protected override void OnControlAdded(ControlEventArgs e){base.OnControlAdded(e);e.Control.Enter+=(s,a)=>{var c=(Control)s;if(c.Top<0)ScrollTo(offset+c.Top);else if(c.Bottom>Height)ScrollTo(offset+c.Bottom-Height);};}
    void ScrollTo(int value){value=Math.Max(0,Math.Min(maximum,value));if(value==offset)return;moving=true;SuspendLayout();int delta=offset-value;offset=value;foreach(Control c in Controls)c.Top+=delta;ResumeLayout(false);moving=false;Invalidate(true);}
    protected override void OnMouseWheel(MouseEventArgs e){ScrollTo(offset-e.Delta*P(42)/120);base.OnMouseWheel(e);}
    Rectangle Thumb(){int h=Math.Max(P(30),Height*Height/Math.Max(1,Height+maximum));int y=maximum==0?0:offset*(Height-h)/maximum;return new Rectangle(Width-P(6),y,P(4),h);}
    protected override void OnPaint(PaintEventArgs e){base.OnPaint(e);if(maximum==0)return;e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;using(var shape=Popup.Round(Thumb(),Math.Max(1,P(2))))using(var fill=new SolidBrush(Color.FromArgb(dragging?180:100,183,202,230)))e.Graphics.FillPath(fill,shape);}
    protected override void OnMouseDown(MouseEventArgs e){base.OnMouseDown(e);if(maximum==0||e.Button!=MouseButtons.Left||e.X<Width-P(12))return;var thumb=Thumb();if(!thumb.Contains(e.Location))ScrollTo((e.Y-thumb.Height/2)*maximum/Math.Max(1,Height-thumb.Height));dragging=true;dragY=e.Y;dragOffset=offset;Capture=true;}
    protected override void OnMouseMove(MouseEventArgs e){base.OnMouseMove(e);if(dragging)ScrollTo(dragOffset+(e.Y-dragY)*maximum/Math.Max(1,Height-Thumb().Height));}
    protected override void OnMouseCaptureChanged(EventArgs e){base.OnMouseCaptureChanged(e);if(!Capture){dragging=false;Invalidate();}}
    protected override void OnMouseUp(MouseEventArgs e){base.OnMouseUp(e);dragging=false;Capture=false;Invalidate();}
}
sealed class TrayCheckBox:CheckBox {
    public Color Tint;
    public TrayCheckBox(){AutoSize=false;FlatStyle=FlatStyle.Flat;Cursor=Cursors.Hand;Font=Popup.FontFor(10,false);SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint,true);}
    protected override void OnMouseEnter(EventArgs e){base.OnMouseEnter(e);Invalidate();}
    protected override void OnMouseLeave(EventArgs e){base.OnMouseLeave(e);Invalidate();}
    protected override void OnPaint(PaintEventArgs e){
        var popup=FindForm() as Popup;if(popup==null){base.OnPaint(e);return;}
        var offset=popup.PointToClient(PointToScreen(Point.Empty));var state=e.Graphics.Save();e.Graphics.TranslateTransform(-offset.X,-offset.Y);popup.PaintBackdrop(e.Graphics,popup.ClientRectangle);e.Graphics.Restore(state);
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var shape=Popup.Round(new Rectangle(0,0,Width-1,Height-1),popup.Pixels(9)))using(var fill=new SolidBrush(Color.FromArgb(Focused||ClientRectangle.Contains(PointToClient(Cursor.Position))?42:20,180,200,235)))e.Graphics.FillPath(fill,shape);
        int size=popup.Pixels(14),left=popup.Pixels(11),top=(Height-size)/2;
        using(var shape=Popup.Round(new Rectangle(left,top,size,size),popup.Pixels(4))){using(var fill=new SolidBrush(Checked?Tint:Color.FromArgb(30,190,210,240)))e.Graphics.FillPath(fill,shape);using(var pen=new Pen(Color.FromArgb(90,200,217,241)))e.Graphics.DrawPath(pen,shape);}
        if(Checked)using(var pen=new Pen(Color.White,Math.Max(1,popup.Pixels(1)))){e.Graphics.DrawLines(pen,new[]{new Point(left+size/4,top+size/2),new Point(left+size*7/16,top+size*11/16),new Point(left+size*3/4,top+size/3)});}
        int x=popup.Pixels(35);var parts=Text.Split(new[]{" · "},StringSplitOptions.None);
        var flags=TextFormatFlags.Left|TextFormatFlags.VerticalCenter|TextFormatFlags.SingleLine|TextFormatFlags.EndEllipsis|TextFormatFlags.NoPrefix|TextFormatFlags.PreserveGraphicsClipping|TextFormatFlags.PreserveGraphicsTranslateTransform;
        if(parts.Length==2){int detailWidth=TextRenderer.MeasureText(parts[1],Popup.FontFor(9,false)).Width+popup.Pixels(8);TextRenderer.DrawText(e.Graphics,parts[0],Font,new Rectangle(x,0,Math.Max(1,Width-x-detailWidth-popup.Pixels(12)),Height),ForeColor,flags);TextRenderer.DrawText(e.Graphics,parts[1],Popup.FontFor(9,false),new Rectangle(Width-detailWidth-popup.Pixels(8),0,detailWidth,Height),Color.FromArgb(176,191,212),(flags&~TextFormatFlags.Left)|TextFormatFlags.Right);}
        else TextRenderer.DrawText(e.Graphics,Text,Font,new Rectangle(x,0,Width-x-popup.Pixels(8),Height),ForeColor,flags);
        if(Focused&&ShowFocusCues)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(ClientRectangle,-popup.Pixels(3),-popup.Pixels(3)),ForeColor,BackColor);
    }
}
sealed class TrayGpuCard:Control {
    readonly string name,installed,latest,status;
    internal bool Green {get{return status=="current"||status=="ahead"||status=="unknown";}}
    internal string StatusText {get{return status=="current"?"Current":status=="ahead"?"Newer":status=="update"?"Update available":"Unknown";}}
    public TrayGpuCard(System.Collections.Generic.Dictionary<string,object> gpu){
        name=Convert.ToString(gpu["name"]);installed=Convert.ToString(gpu["installed"]);status=Convert.ToString(gpu["status"]);latest=gpu.ContainsKey("latest")?Convert.ToString(gpu["latest"]):"";
        AccessibleRole=AccessibleRole.Grouping;AccessibleName=name;AccessibleDescription="Installed "+installed+". Status: "+StatusText;TabStop=false;
        SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint,true);
    }
    protected override void OnPaint(PaintEventArgs e){
        var popup=FindForm() as Popup;if(popup==null)return;
        var offset=popup.PointToClient(PointToScreen(Point.Empty));var state=e.Graphics.Save();e.Graphics.TranslateTransform(-offset.X,-offset.Y);popup.PaintBackdrop(e.Graphics,popup.ClientRectangle);e.Graphics.Restore(state);
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var shape=Popup.Round(new Rectangle(0,0,Width-1,Height-1),popup.Pixels(11)))using(var fill=new SolidBrush(Color.FromArgb(24,180,200,235)))e.Graphics.FillPath(fill,shape);
        var flags=TextFormatFlags.Left|TextFormatFlags.VerticalCenter|TextFormatFlags.NoPrefix|TextFormatFlags.PreserveGraphicsClipping|TextFormatFlags.PreserveGraphicsTranslateTransform;
        TextRenderer.DrawText(e.Graphics,name,Popup.FontFor(10,true),new Rectangle(popup.Pixels(13),popup.Pixels(9),Width-popup.Pixels(26),popup.Pixels(32)),Color.FromArgb(242,244,248),flags|TextFormatFlags.WordBreak);
        int badgeWidth=popup.Pixels(status=="update"?104:76);
        var badge=new Rectangle(Width-badgeWidth-popup.Pixels(13),popup.Pixels(52),badgeWidth,popup.Pixels(24));
        var tint=Green?Color.FromArgb(61,220,151):Color.FromArgb(255,190,61);
        using(var shape=Popup.Round(badge,popup.Pixels(7)))using(var fill=new SolidBrush(Color.FromArgb(24,tint)))e.Graphics.FillPath(fill,shape);
        TextRenderer.DrawText(e.Graphics,StatusText,Popup.FontFor(9,true),badge,tint,flags|TextFormatFlags.HorizontalCenter|TextFormatFlags.SingleLine);
        int textWidth=Math.Max(1,badge.Left-popup.Pixels(22));
        TextRenderer.DrawText(e.Graphics,"Installed",Popup.FontFor(8,false),new Rectangle(popup.Pixels(13),popup.Pixels(43),textWidth,popup.Pixels(16)),Color.FromArgb(176,191,212),flags|TextFormatFlags.SingleLine);
        TextRenderer.DrawText(e.Graphics,installed,Popup.FontFor(10,true),new Rectangle(popup.Pixels(13),popup.Pixels(60),textWidth,popup.Pixels(22)),Color.FromArgb(232,238,248),flags|TextFormatFlags.SingleLine|TextFormatFlags.EndEllipsis);
        if(status=="update"&&latest!="")TextRenderer.DrawText(e.Graphics,"Latest  "+latest,Popup.FontFor(9,false),new Rectangle(popup.Pixels(13),popup.Pixels(85),Width-popup.Pixels(26),popup.Pixels(18)),Color.FromArgb(176,191,212),flags|TextFormatFlags.SingleLine);
    }
}

}
