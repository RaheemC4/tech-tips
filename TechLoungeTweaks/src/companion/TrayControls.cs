using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;
namespace TechLounge {
// Fixed content area; every item is laid out together without scrollbars.
sealed class TrayBodyPanel:Panel {
    protected override void WndProc(ref Message message){TrayGeometry.DiscardCopiedPixels(ref message,true);base.WndProc(ref message);}
    public TrayBodyPanel(){AutoScroll=false;DoubleBuffered=true;SetStyle(ControlStyles.ResizeRedraw,true);}
}
sealed class TrayCheckBox:CheckBox {
    public Color Tint;
    public TrayCheckBox(){AutoSize=false;FlatStyle=FlatStyle.Flat;Cursor=PopupDpi.HandCursor();Font=Popup.FontFor(10,false);SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint,true);}
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
        if(parts.Length==2){int detailWidth=TextRenderer.MeasureText(parts[1],popup.FontAt(9,false)).Width+popup.Pixels(8);TextRenderer.DrawText(e.Graphics,parts[0],Font,new Rectangle(x,0,Math.Max(1,Width-x-detailWidth-popup.Pixels(12)),Height),ForeColor,flags);TextRenderer.DrawText(e.Graphics,parts[1],popup.FontAt(9,false),new Rectangle(Width-detailWidth-popup.Pixels(8),0,detailWidth,Height),Color.FromArgb(176,191,212),(flags&~TextFormatFlags.Left)|TextFormatFlags.Right);}
        else TextRenderer.DrawText(e.Graphics,Text,Font,new Rectangle(x,0,Width-x-popup.Pixels(8),Height),ForeColor,flags);
        if(Focused&&ShowFocusCues)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(ClientRectangle,-popup.Pixels(3),-popup.Pixels(3)),ForeColor,BackColor);
    }
}
sealed class TrayGpuCard:Control {
    readonly string name,installed,latest,status;
    internal bool Green {get{return status=="current"||status=="ahead";}}
    internal string StatusText {get{return status=="current"?"Up to date":status=="ahead"?"Newer":status=="update"?"Out of date":"Couldn’t verify";}}
    static int NameHeight(string text,Popup popup,int width){return Math.Max(popup.Pixels(32),TextRenderer.MeasureText(text,popup.FontAt(10,true),new Size(Math.Max(1,width-popup.Pixels(57)),int.MaxValue),TextFormatFlags.WordBreak|TextFormatFlags.NoPrefix).Height);}
    internal static int HeightFor(System.Collections.Generic.Dictionary<string,object> gpu,Popup popup,int width){return (Convert.ToString(gpu["status"])=="update"?110:92)+Math.Max(0,popup.Logical(NameHeight(Convert.ToString(gpu["name"]),popup,popup.Pixels(width)))-32);}
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
        TraySymbols.Draw(e.Graphics,"gpu",new Rectangle(popup.Pixels(13),popup.Pixels(12),popup.Pixels(22),popup.Pixels(22)),Green?Color.FromArgb(61,220,151):status=="update"?Color.FromArgb(255,190,61):Color.FromArgb(176,191,212));
        int nameHeight=NameHeight(name,popup,Width),extra=nameHeight-popup.Pixels(32);
        TextRenderer.DrawText(e.Graphics,name,popup.FontAt(10,true),new Rectangle(popup.Pixels(44),popup.Pixels(9),Width-popup.Pixels(57),nameHeight),Color.FromArgb(242,244,248),flags|TextFormatFlags.WordBreak);
        int badgeWidth=popup.Pixels(status=="unknown"?116:104);
        var badge=new Rectangle(Width-badgeWidth-popup.Pixels(13),popup.Pixels(52)+extra,badgeWidth,popup.Pixels(24));
        var tint=Green?Color.FromArgb(61,220,151):status=="update"?Color.FromArgb(255,190,61):Color.FromArgb(176,191,212);
        using(var shape=Popup.Round(badge,popup.Pixels(7)))using(var fill=new SolidBrush(Color.FromArgb(24,tint)))e.Graphics.FillPath(fill,shape);
        TextRenderer.DrawText(e.Graphics,StatusText,popup.FontAt(9,true),badge,tint,flags|TextFormatFlags.HorizontalCenter|TextFormatFlags.SingleLine);
        int textWidth=Math.Max(1,badge.Left-popup.Pixels(22));
        TextRenderer.DrawText(e.Graphics,"Installed",popup.FontAt(8,false),new Rectangle(popup.Pixels(13),popup.Pixels(43)+extra,textWidth,popup.Pixels(16)),Color.FromArgb(176,191,212),flags|TextFormatFlags.SingleLine);
        TextRenderer.DrawText(e.Graphics,installed,popup.FontAt(10,true),new Rectangle(popup.Pixels(13),popup.Pixels(60)+extra,textWidth,popup.Pixels(22)),Color.FromArgb(232,238,248),flags|TextFormatFlags.SingleLine|TextFormatFlags.EndEllipsis);
        if(status=="update"&&latest!="")TextRenderer.DrawText(e.Graphics,"Latest  "+latest,popup.FontAt(9,false),new Rectangle(popup.Pixels(13),popup.Pixels(85)+extra,Width-popup.Pixels(26),popup.Pixels(18)),Color.FromArgb(176,191,212),flags|TextFormatFlags.SingleLine);
    }
}

// Result metrics remain semantic controls; icons are drawn paths, never font glyphs.
sealed class TrayMetricCard:Control {
    readonly string title,icon;readonly Color accent;
    readonly Timer numbers=new Timer{Interval=16};readonly System.Diagnostics.Stopwatch transition=new System.Diagnostics.Stopwatch();double shown,target,velocity;bool hasNumber;
    internal string Value,Caption;internal Color StatusColor;
    internal static string Number(object raw,bool speed){
        double value;if(raw==null||!double.TryParse(Convert.ToString(raw,System.Globalization.CultureInfo.InvariantCulture),System.Globalization.NumberStyles.Float,System.Globalization.CultureInfo.InvariantCulture,out value)||double.IsNaN(value)||double.IsInfinity(value)||value<0||(speed&&value==0))return "Unavailable";
        return value.ToString(value>=1000?"0":value>=10?"0.0":"0.##",System.Globalization.CultureInfo.CurrentCulture);
    }
    internal TrayMetricCard(string title,object raw,string unit,string icon,Color accent){
        this.title=title;this.icon=icon;this.accent=accent;
        AccessibleRole=AccessibleRole.StaticText;TabStop=false;
        SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint,true);
        numbers.Tick+=(s,e)=>{
            double dt=transition.Elapsed.TotalSeconds;transition.Restart();double delta=shown-target,omega=8,decay=Math.Exp(-omega*dt),travel=velocity+omega*delta;
            shown=target+(delta+travel*dt)*decay;velocity=(velocity-omega*travel*dt)*decay;
            if(Math.Abs(shown-target)<.01&&Math.Abs(velocity)<.05){shown=target;velocity=0;numbers.Stop();}
            Value=Number(Math.Max(0,shown),false);AccessibleName=title+": "+Value+" "+Caption;Invalidate();
        };
        UpdateValue(raw,unit,false,false);
    }
    internal void UpdateValue(object raw,string unit,bool pending,bool testing,bool live=false){
        var good=Color.FromArgb(61,220,151);var warn=Color.FromArgb(255,190,61);var muted=Color.FromArgb(176,191,212);
        double speed;
        if(live&&(icon=="download"||icon=="upload")&&double.TryParse(Convert.ToString(raw,System.Globalization.CultureInfo.InvariantCulture),System.Globalization.NumberStyles.Float,System.Globalization.CultureInfo.InvariantCulture,out speed)&&speed<=0){pending=true;testing=true;}
        if(pending){Value="…";Caption=testing?"Testing…":"Waiting";StatusColor=accent;}
        else if(icon=="grade"){
            string grade=Convert.ToString(raw);Value=Array.IndexOf(new[]{"A+","A","B","C","D","F"},grade)>=0?grade:"Unavailable";
            StatusColor=grade=="A+"||grade=="A"?good:grade=="B"||grade=="C"||grade=="D"?warn:grade=="F"?Color.FromArgb(255,93,108):muted;
            Caption=grade=="A+"?"Excellent":grade=="A"?"Great":grade=="B"?"Good":grade=="C"?"Fair":grade=="D"?"Poor":grade=="F"?"Heavy lag":"Not measured";
        }else{Value=Number(raw,!live&&(icon=="download"||icon=="upload"));StatusColor=Value=="Unavailable"?muted:Color.FromArgb(242,244,248);Caption=Value=="Unavailable"?"Not measured":unit;}
        if(live&&!pending)Caption=icon=="grade"?"Live estimate":icon=="latency"?unit:"Mbps · Live";
        double numeric;if(!pending&&icon!="grade"&&Value!="Unavailable"&&double.TryParse(Convert.ToString(raw,System.Globalization.CultureInfo.InvariantCulture),System.Globalization.NumberStyles.Float,System.Globalization.CultureInfo.InvariantCulture,out numeric)){
            if(hasNumber&&PopupMotion.Enabled()&&Visible){target=numeric;if(!numbers.Enabled){transition.Restart();numbers.Start();}Value=Number(shown,false);}else{numbers.Stop();velocity=0;shown=target=numeric;}hasNumber=true;
        }else{numbers.Stop();velocity=0;hasNumber=false;}
        AccessibleName=title+": "+Value+" "+Caption;Invalidate();
    }
    protected override void OnVisibleChanged(EventArgs e){base.OnVisibleChanged(e);if(!Visible&&numbers!=null)numbers.Stop();}
    protected override void Dispose(bool disposing){if(disposing){numbers.Stop();numbers.Dispose();transition.Stop();}base.Dispose(disposing);}
    protected override void OnPaint(PaintEventArgs e){
        var popup=FindForm() as Popup;if(popup==null)return;int pad=popup.Pixels(14);
        var offset=popup.PointToClient(PointToScreen(Point.Empty));var state=e.Graphics.Save();e.Graphics.TranslateTransform(-offset.X,-offset.Y);popup.PaintBackdrop(e.Graphics,popup.ClientRectangle);e.Graphics.Restore(state);
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var shape=Popup.Round(new Rectangle(0,0,Width-1,Height-1),popup.Pixels(14))){using(var fill=new SolidBrush(Color.FromArgb(28,180,200,235)))e.Graphics.FillPath(fill,shape);using(var rim=new Pen(Color.FromArgb(22,220,235,255)))e.Graphics.DrawPath(rim,shape);}
        Color tint=icon=="grade"?StatusColor:accent;
        var saved=e.Graphics.Save();e.Graphics.TranslateTransform(pad,popup.Pixels(9));e.Graphics.ScaleTransform(popup.Pixels(18)/22f,popup.Pixels(18)/22f);
        using(var pen=new Pen(tint,1.8f)){pen.StartCap=pen.EndCap=LineCap.Round;pen.LineJoin=LineJoin.Round;
            if(icon=="download"||icon=="upload"){bool down=icon=="download";e.Graphics.DrawLine(pen,11,down?3:17,11,down?17:3);e.Graphics.DrawLines(pen,down?new[]{new Point(6,12),new Point(11,17),new Point(16,12)}:new[]{new Point(6,8),new Point(11,3),new Point(16,8)});e.Graphics.DrawLine(pen,4,20,18,20);}
            else if(icon=="latency")e.Graphics.DrawLines(pen,new[]{new Point(1,12),new Point(6,12),new Point(9,4),new Point(13,19),new Point(16,10),new Point(21,10)});
            else {e.Graphics.DrawEllipse(pen,2,2,18,18);e.Graphics.DrawLines(pen,new[]{new Point(6,11),new Point(10,15),new Point(16,8)});}
        }e.Graphics.Restore(saved);
        var flags=TextFormatFlags.Left|TextFormatFlags.VerticalCenter|TextFormatFlags.SingleLine|TextFormatFlags.NoPrefix|TextFormatFlags.EndEllipsis|TextFormatFlags.PreserveGraphicsClipping|TextFormatFlags.PreserveGraphicsTranslateTransform;
        TextRenderer.DrawText(e.Graphics,title,popup.FontAt(9,true),new Rectangle(pad+popup.Pixels(25),popup.Pixels(6),Width-pad*2-popup.Pixels(25),popup.Pixels(20)),Color.FromArgb(208,220,238),flags);
        TextRenderer.DrawText(e.Graphics,Value,popup.FontAt(Value=="Unavailable"?12:22,true),new Rectangle(pad,popup.Pixels(34),Width-pad*2,popup.Pixels(34)),StatusColor,flags);
        TextRenderer.DrawText(e.Graphics,Caption,popup.FontAt(9,false),new Rectangle(pad,popup.Pixels(72),Width-pad*2,popup.Pixels(18)),Value=="Unavailable"?Color.FromArgb(255,190,61):Color.FromArgb(176,191,212),flags);
    }
}

}
