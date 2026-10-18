using System;using System.Drawing;using System.Drawing.Drawing2D;using System.Windows.Forms;
namespace TechLounge {
static class TraySymbols {
    internal static void Draw(Graphics g,string icon,Rectangle bounds,Color tint){
        var state=g.Save();g.TranslateTransform(bounds.X,bounds.Y);g.ScaleTransform(bounds.Width/24f,bounds.Height/24f);g.SmoothingMode=SmoothingMode.AntiAlias;
        using(var pen=new Pen(tint,1.7f)){pen.StartCap=pen.EndCap=LineCap.Round;pen.LineJoin=LineJoin.Round;
            if(icon=="clean"){g.DrawRectangle(pen,6,7,12,14);g.DrawLine(pen,4,7,20,7);g.DrawLine(pen,9,3,15,3);g.DrawLine(pen,10,11,10,17);g.DrawLine(pen,14,11,14,17);}
            else if(icon=="gpu"){g.DrawRectangle(pen,3,5,18,13);g.DrawEllipse(pen,9,8,6,6);g.DrawLine(pen,8,21,16,21);g.DrawLine(pen,12,18,12,21);}
            else if(icon=="power"){g.DrawLines(pen,new[]{new Point(13,2),new Point(5,13),new Point(11,13),new Point(10,22),new Point(19,10),new Point(13,10),new Point(13,2)});}
            else if(icon=="network"){g.DrawArc(pen,2,4,20,20,220,100);g.DrawArc(pen,6,9,12,12,220,100);g.DrawArc(pen,9,14,6,6,220,100);g.DrawEllipse(pen,11,20,2,2);}
            else if(icon=="restore"){g.DrawArc(pen,4,4,16,16,225,300);g.DrawLines(pen,new[]{new Point(3,3),new Point(3,9),new Point(9,9)});g.DrawLine(pen,12,7,12,12);g.DrawLine(pen,12,12,16,14);}
            else if(icon=="startup"){g.DrawRectangle(pen,3,5,18,15);g.DrawLine(pen,3,9,21,9);g.DrawLines(pen,new[]{new Point(9,12),new Point(15,15),new Point(9,18),new Point(9,12)});}
            else if(icon=="check"){g.DrawEllipse(pen,2,2,20,20);g.DrawLines(pen,new[]{new Point(6,12),new Point(10,16),new Point(18,8)});}
            else {g.DrawEllipse(pen,2,2,20,20);g.DrawLine(pen,12,7,12,13);g.DrawEllipse(pen,11.5f,17,1,1);}
        }g.Restore(state);
    }
}
sealed class TraySymbolBadge:Control {
    readonly string icon;readonly Color tint;
    internal TraySymbolBadge(string icon,Color tint){this.icon=icon;this.tint=tint;TabStop=false;SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint,true);}
    protected override void OnPaint(PaintEventArgs e){var popup=FindForm() as Popup;if(popup==null)return;var offset=popup.PointToClient(PointToScreen(Point.Empty));popup.PaintBackdrop(e.Graphics,new Rectangle(-offset.X,-offset.Y,popup.Width,popup.Height));TraySymbols.Draw(e.Graphics,icon,ClientRectangle,tint);}
}
}
