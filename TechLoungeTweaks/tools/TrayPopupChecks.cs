using System;using System.Drawing;using System.IO;using System.Reflection;using System.Windows.Forms;using System.Diagnostics;
class Checks {
 static BindingFlags F=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
 static void Pump(){var sw=Stopwatch.StartNew();while(sw.ElapsedMilliseconds<180){Application.DoEvents();System.Threading.Thread.Sleep(5);}}
 static Control FindPlan(Control c){if(c.AccessibleName=="Power plan")return c;foreach(Control child in c.Controls){var found=FindPlan(child);if(found!=null)return found;}return null;} static Bitmap Paint(Control c,Color seed){var b=new Bitmap(c.Width,c.Height);using(var g=Graphics.FromImage(b)){g.Clear(seed);var e=new PaintEventArgs(g,c.ClientRectangle);c.GetType().GetMethod("OnPaintBackground",F).Invoke(c,new object[]{e});c.GetType().GetMethod("OnPaint",F).Invoke(c,new object[]{e});}return b;}
 [STAThread]static int Main(string[] a){try{Application.EnableVisualStyles();var asm=Assembly.LoadFrom(a[0]);var bt=asm.GetType("TechLounge.GlassButton");using(var c=(Control)Activator.CreateInstance(bt)){c.Size=new Size(220,80);c.Text="Connection\nSpeed & latency";using(var x=Paint(c,Color.Magenta))using(var y=Paint(c,Color.Lime)){for(int j=0;j<x.Height;j++)for(int i=0;i<x.Width;i++)if(x.GetPixel(i,j)!=y.GetPixel(i,j))throw new Exception("Paint depends on stale pixels");x.Save(a[1]+"/button-clean.png");}}
 var tt=asm.GetType("TechLounge.Tray");var pt=asm.GetType("TechLounge.Popup");
 using(var tray=(IDisposable)Activator.CreateInstance(tt,F,null,new object[]{true},null))using(var popup=(Form)Activator.CreateInstance(pt,F,null,new object[]{tray},null))using(var outside=new Form{Text="Tray dismissal check",Size=new Size(240,120),StartPosition=FormStartPosition.Manual,Location=new Point(30,30)}){
 popup.Show();popup.Activate();Pump();if(!popup.ContainsFocus)throw new Exception("Popup did not receive focus");
 using(var b=new Bitmap(popup.Width,popup.Height)){popup.DrawToBitmap(b,popup.ClientRectangle);b.Save(a[1]+"/popup-clean.png");}
 var plan=FindPlan(popup);plan.ContextMenuStrip.Show(plan,new Point(0,plan.Height));Pump();if(popup.IsDisposed)throw new Exception("Dropdown dismissed its popup");plan.ContextMenuStrip.Close();popup.Activate();Pump();if(popup.IsDisposed)throw new Exception("Closing dropdown dismissed its popup");outside.Show();outside.Activate();Pump();if(!popup.IsDisposed)throw new Exception("Popup did not dismiss after outside focus");outside.Close();}
 File.WriteAllText(a[1]+"/popup-checks.txt","PASS: button repaint independent of stale pixels; real popup received focus; power dropdown opened and closed without dismissing parent; external foreground window dismissed popup; no app action ran.");return 0;
 }catch(Exception e){File.WriteAllText(a[1]+"/popup-checks.txt",e.ToString());return 1;}}
}

