using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;

namespace TechLounge {
sealed class ThemeMenu:ContextMenuStrip {
    public ThemeMenu(){DropShadowEnabled=true;ShowImageMargin=false;}
    protected override void OnSizeChanged(EventArgs e){
        base.OnSizeChanged(e);
        if(Width<24||Height<24)return;
        int radius=(int)Math.Round(11*PopupDpi.PointerScale());
        using(var path=Popup.Round(ClientRectangle,radius)){
            var old=Region;Region=new Region(path);if(old!=null)old.Dispose();
        }
    }
}
sealed class ThemeMenuRenderer:ToolStripRenderer {
    readonly Color accent;readonly float scale;
    public ThemeMenuRenderer(Color accent,float scale){this.accent=accent;this.scale=scale;}
    int P(float n){return (int)Math.Round(n*scale);}
    Color Tint(int r,int g,int b,int divisor){return Color.FromArgb(r+accent.R/divisor,g+accent.G/divisor,b+accent.B/divisor);}
    protected override void OnRenderToolStripBackground(ToolStripRenderEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        var box=new Rectangle(0,0,e.ToolStrip.Width-1,e.ToolStrip.Height-1);
        using(var path=Popup.Round(box,P(11)))
        using(var fill=new LinearGradientBrush(box,Tint(29,38,53,7),Tint(22,30,43,10),70f))e.Graphics.FillPath(fill,path);
    }
    protected override void OnRenderToolStripBorder(ToolStripRenderEventArgs e){
        using(var path=Popup.Round(new Rectangle(0,0,e.ToolStrip.Width-1,e.ToolStrip.Height-1),P(11)))
        using(var pen=new Pen(Color.FromArgb(70,154,174,205)))e.Graphics.DrawPath(pen,path);
    }
    protected override void OnRenderMenuItemBackground(ToolStripItemRenderEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        if(e.Item.Selected&&e.Item.Enabled){
            using(var path=Popup.Round(new Rectangle(P(1),P(1),e.Item.Width-P(2),e.Item.Height-P(2)),P(7)))
            using(var fill=new SolidBrush(Tint(45,55,72,5)))e.Graphics.FillPath(fill,path);
        }
        var option=e.Item as ToolStripMenuItem;
        if(option!=null&&option.Checked)using(var pen=new Pen(Color.FromArgb(193,218,255),Math.Max(1,P(1.4f)))){
            int x=e.Item.Width-P(23),y=e.Item.Height/2;
            e.Graphics.DrawLines(pen,new[]{new Point(x,y),new Point(x+P(3),y+P(3)),new Point(x+P(9),y-P(4))});
        }
        string glyph=e.Item.Tag as string;
        if(glyph==null)return;
        var state=e.Graphics.Save();e.Graphics.TranslateTransform(P(13),(e.Item.Height-P(16))/2f);e.Graphics.ScaleTransform(scale,scale);
        using(var pen=new Pen(e.Item.Enabled?Color.FromArgb(187,207,236):Color.Gray,1.35f)){
            pen.StartCap=pen.EndCap=LineCap.Round;
            if(glyph=="quick"){
                for(int i=0;i<3;i++){float y=3+i*5;float x=i==1?11:5;e.Graphics.DrawLine(pen,1,y,15,y);using(var fill=new SolidBrush(Tint(29,38,53,7)))e.Graphics.FillEllipse(fill,x-2,y-2,4,4);e.Graphics.DrawEllipse(pen,x-2,y-2,4,4);}
            }else if(glyph=="open"){
                e.Graphics.DrawRectangle(pen,1,2,14,12);e.Graphics.DrawLine(pen,1,6,15,6);
            }else if(glyph=="exit"){
                e.Graphics.DrawArc(pen,2,2,12,12,-55,290);e.Graphics.DrawLine(pen,8,0,8,8);
            }
        }
        e.Graphics.Restore(state);
    }
    protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e){
        int left=P(e.Item.Tag is string?40:12);
        var box=new Rectangle(left,0,e.Item.Width-left-P(e.Item.Tag is string?12:32),e.Item.Height);
        TextRenderer.DrawText(e.Graphics,e.Text,e.TextFont,box,e.Item.Enabled?e.Item.ForeColor:SystemColors.GrayText,
            TextFormatFlags.Left|TextFormatFlags.VerticalCenter|TextFormatFlags.SingleLine|TextFormatFlags.NoPrefix|TextFormatFlags.PreserveGraphicsClipping|TextFormatFlags.PreserveGraphicsTranslateTransform);
    }
    protected override void OnRenderSeparator(ToolStripSeparatorRenderEventArgs e){
        using(var pen=new Pen(Color.FromArgb(42,171,190,217)))e.Graphics.DrawLine(pen,P(11),e.Item.Height/2,e.Item.Width-P(11),e.Item.Height/2);
    }
}
}
