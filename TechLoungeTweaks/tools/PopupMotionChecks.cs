using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace TechLounge {
static class PopupMotionChecks {
    static void Pump(int duration,Action sample=null){
        var watch=Stopwatch.StartNew();
        while(watch.ElapsedMilliseconds<duration){Application.DoEvents();if(sample!=null)sample();System.Threading.Thread.Sleep(4);}
        Application.DoEvents();
    }
    static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
    static GlassButton Plan(Control parent){
        if(parent.AccessibleName=="Power plan")return (GlassButton)parent;
        foreach(Control child in parent.Controls){var result=Plan(child);if(result!=null)return result;}return null;
    }
    static void Motion(){
        using(var window=new Form{Location=new Point(40,40),StartPosition=FormStartPosition.Manual,Size=new Size(180,100),ShowInTaskbar=false})
        using(var motion=new PopupMotion(window,18,true)){
            window.Shown+=(s,e)=>motion.Show();window.Show();
            Require(window.Opacity==0,"Opening must start invisible");
            var tops=new List<int>();var alpha=new List<double>();
            Pump(420,()=>{tops.Add(window.Top);alpha.Add(window.Opacity);});
            Require(tops.Exists(y=>y<40),"Entrance did not spring past its resting position");
            Require(alpha.Exists(a=>a>0&&a<1),"Entrance did not fade progressively");
            Require(window.Top==40&&window.Opacity==1,"Opening did not settle exactly");
            window.Close();Require(!window.IsDisposed,"Close skipped its animation");Pump(55);
            int top=window.Top;double opacity=window.Opacity;
            Require(opacity>0&&opacity<1,"Close did not fade progressively");
            motion.Reopen();Require(window.Top==top&&window.Opacity==opacity,"Reopening jumped to a different pose");
            Pump(420);Require(!window.IsDisposed&&window.Top==40&&window.Opacity==1,"Interrupted close did not reopen");
            window.Close();Pump(250);Require(window.IsDisposed,"Animated close never completed");
        }
        using(var window=new Form{ShowInTaskbar=false})using(var motion=new PopupMotion(window,18,false)){
            window.Shown+=(s,e)=>motion.Show();window.Show();Require(window.Opacity==1,"Reduced motion hid the window");
            window.Close();Require(window.IsDisposed,"Reduced motion delayed closure");
        }
    }
    static void Dropdown(){
        using(var tray=new Tray(true))using(var popup=new Popup(tray))
        using(var outside=new Form{ShowInTaskbar=false,Location=new Point(20,20),StartPosition=FormStartPosition.Manual,Size=new Size(160,100)}){
            var plan=Plan(popup);
            var work=Screen.FromPoint(Cursor.Position).WorkingArea;popup.Location=new Point(work.Left+40,work.Top+40);
            popup.Show();popup.Activate();Pump(420);plan.Focus();var menu=plan.ContextMenuStrip;
            plan.PerformClick();Pump(30);Require(menu.Visible,"Power selector did not open");
            // Model the native menu dismissing itself on the selector's mouse-down,
            // followed by the selector receiving the same click on mouse-up.
            var oldPointer=Cursor.Position;Cursor.Position=plan.PointToScreen(new Point(plan.Width/2,plan.Height/2));
            Require(plan.ClientRectangle.Contains(plan.PointToClient(Cursor.Position)),"Pointer did not reach selector: "+Cursor.Position+" versus "+plan.PointToScreen(Point.Empty)+" size "+plan.Size);
            menu.Close(ToolStripDropDownCloseReason.AppClicked);popup.Activate();plan.PerformClick();Cursor.Position=oldPointer;Pump(30);
            Require(!menu.Visible,"The selector reopened the menu on its dismissal click");
            Pump(520);plan.PerformClick();Pump(30);Require(menu.Visible,"A later click could not reopen the menu");
            plan.PerformClick();Pump(30);Require(!menu.Visible,"Visible menu did not toggle closed");
            Require(((ToolStripMenuItem)menu.Items[0]).Checked,"Active power plan lacked a selected marker");
            tray.Window=popup;menu.Items[0].PerformClick();Pump(30);
            Require(Plan(popup)!=null,"Power selection navigated to a confirmation screen");
            Require(!Plan(popup).Enabled,"Power selector allowed overlapping changes");
            tray.Jobs["power"]=new Job{Message="Permission denied."};popup.Render();
            bool errorVisible=false;foreach(Control c in popup.Controls)foreach(Control child in c.Controls)if(child is Label&&child.Text=="Permission denied.")errorVisible=true;
            Require(errorVisible,"Power switch failure disappeared silently");
            var verified=new Dictionary<string,object>{{"plans",new object[]{new Dictionary<string,object>{{"id","ultimate"},{"name","Ultimate Performance"},{"active",true}}}}};
            tray.Jobs["power"]=new Job{Result=verified};tray.Jobs["plans"]=tray.Jobs["power"];popup.Render();
            Require(Plan(popup).Text.StartsWith("Ultimate Performance plan"),"Verified selection did not update the dropdown label");
            Require(((ToolStripMenuItem)Plan(popup).ContextMenuStrip.Items[0]).Checked,"Verified selection did not update its marker");
            Pump(250);Require(popup.Visible&&!popup.IsDisposed,"Atomic page redraw dismissed the popup");
            var handle=popup.Handle;popup.Close();Pump(45);popup.Reveal();Pump(420);
            Require(!popup.IsDisposed&&popup.Handle==handle,"Rapid tray reopening recreated the popup");
            outside.Show();outside.Activate();Pump(300);Require(popup.IsDisposed,"Outside activation did not finish dismissal");
        }
    }
    static void Appearance(){
        using(var tray=new Tray(true))using(var menu=tray.CreateMenu()){
            bool invoked=false;
            menu.Items.Add("Quick actions",null,(s,e)=>invoked=true).Tag="quick";
            menu.Items.Add("Open app").Tag="open";menu.Items.Add(new ToolStripSeparator());menu.Items.Add("Exit companion").Tag="exit";
            menu.Show(new Point(40,40));Pump(40);
            Require(menu.Region!=null&&!menu.Region.IsVisible(0,0),"Menu corners remained square");
            foreach(ToolStripItem item in menu.Items)if(!(item is ToolStripSeparator)){
                int reserve=(int)Math.Round(56*PopupDpi.PointerScale());
                Require(item.Width>=TextRenderer.MeasureText(item.Text,menu.Font).Width+reserve,"Menu clipped its icon/text padding");
            }
            menu.Items[0].Select();Require(menu.Items[0].Selected,"Menu selection failed");menu.Items[0].PerformClick();Require(invoked,"Menu action failed");menu.Close();
            var entries=new List<object>();for(int i=0;i<12;i++)entries.Add(new Dictionary<string,object>{{"id","fixture"+i},{"name","Temporary files "+i},{"human","225 MB"},{"default",true}});
            tray.Jobs["scan"]=new Job{Result=new Dictionary<string,object>{{"items",entries.ToArray()}}};
            using(var popup=new Popup(tray)){
                typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"scan");popup.Render();popup.Show();Pump(420);
                var viewport=(TrayScrollPanel)typeof(Popup).GetField("body",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(popup);
                Require(!viewport.AutoScroll,"Native scrollbar chrome remained enabled");
                int rows=0;foreach(Control c in viewport.Controls)if(c is CheckBox&&c.Bottom<=viewport.Height)rows++;
                Require(rows>=9,"Cleanup still requires scrolling past fewer than nine compact rows on this monitor");
                Button clean=null;foreach(Control c in popup.Controls)if(c is Button&&c.Text=="Clean selected")clean=(Button)c;
                Require(clean!=null&&clean.Bottom<=popup.ClientSize.Height,"Cleanup action did not stay in the footer");
                if(Array.Exists(FontFamily.Families,f=>f.Name=="Segoe UI Variable Text"))Require(Popup.FontFor(10,false).Name=="Segoe UI Variable Text","Tray did not match the app font family");
                CheckBox last=null;foreach(Control c in viewport.Controls)if(c is CheckBox)last=(CheckBox)c;
                Require(last!=null&&last.Focus(),"Cleanup checkboxes lost keyboard focus");Pump(30);
                Require(last.Top>=0&&last.Bottom<=viewport.Height,"Focused cleanup option remained outside the viewport");
                popup.Render();Pump(30);
                foreach(Control c in viewport.Controls)if(c is Label&&c.Text=="Disk cleanup")Require(c.Top==popup.Pixels(42),"Reopening retained a clipped scroll position");
                tray.Jobs["clean"]=new Job{Message="Freed 1.6 GB. Skipped 514 files in use or protected by Windows."};
                typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"clean");popup.Render();Pump(30);
                Button review=null;Label result=null;foreach(Control c in viewport.Controls){if(c is Button&&c.Text=="Review cleanup")review=(Button)c;if(c is Label&&c.Text.StartsWith("Freed 1.6"))result=(Label)c;}
                Require(result!=null&&result.Height<=popup.Pixels(65),"Short result reserved an oversized empty text area");
                Require(review!=null&&review.Bottom<=viewport.Height,"Review cleanup still required scrolling");
                var current=new Dictionary<string,object>{{"name","NVIDIA GeForce RTX 5090"},{"installed","617.42"},{"latest","617.42"},{"status","current"}};
                var unknown=new Dictionary<string,object>{{"name","Intel UHD Graphics 770"},{"installed","32.0.101.7088"},{"latest",null},{"status","unknown"}};
                tray.Jobs["drivers"]=new Job{Result=new Dictionary<string,object>{{"gpus",new object[]{current,unknown}}}};
                typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"drivers");popup.Render();
                int cards=0;bool unknownLabel=false;foreach(Control c in viewport.Controls)if(c is TrayGpuCard){var card=(TrayGpuCard)c;cards++;Require(card.Green,"Current or unknown GPU status lost its requested green treatment");unknownLabel|=card.StatusText=="Unknown";}
                Require(cards==2&&unknownLabel,"Driver cards lost a GPU or misrepresented unknown status");
                Require(FindButton(popup,"Check again").Bottom<=viewport.Height,"Two GPU cards pushed Check again out of view");
                Require(Popup.FontFor(10,true).Bold,"Tray emphasis still used a regular-weight font");
                tray.Window=popup;tray.SetUpdateAvailable(true);Require(FindButton(popup,"● Update available")==null,"Update indicator appeared outside Quick actions");
                typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"home");popup.Render();
                Require(FindButton(popup,"● Update available")!=null,"Available update lacked its compact indicator");
                tray.SetUpdateAvailable(false);Require(FindButton(popup,"● Update available")==null&&FindButton(popup,"Updates")==null,"Tray retained a redundant update control");
                Require(FindButton(popup,"Open app").Width==popup.ClientSize.Width-popup.Pixels(48),"Normal footer retained the empty update column");
                popup.Dispose();
            }
        }
    }
    static Button FindButton(Control parent,string prefix){
        foreach(Control c in parent.Controls){if(c is Button&&c.Text.StartsWith(prefix))return (Button)c;var child=FindButton(c,prefix);if(child!=null)return child;}return null;
    }
    static void ResponsiveProgress(){
        using(var tray=new Tray(true))using(var popup=new Popup(tray)){
            tray.Window=popup;var job=new Job{Running=true,Message="Measuring idle latency"};tray.Jobs["connection"]=job;
            typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"connection");popup.Render();popup.Show();Pump(420);
            var back=FindButton(popup,"‹");Require(back!=null,"Connection screen lacked Back");
            for(int i=0;i<100;i++){job.Message="Testing download "+i;popup.JobChanged("connection");Require(!back.IsDisposed,"Progress replaced the navigation controls");}
            back.PerformClick();var connection=FindButton(popup,"Connection");Require(connection!=null&&job.Running,"Back did not leave the running test");
            for(int i=0;i<100;i++){job.Message="Testing upload "+i;popup.JobChanged("connection");Require(!connection.IsDisposed,"Background progress rebuilt the home screen");}
            connection.PerformClick();Require(object.ReferenceEquals(tray.Jobs["connection"],job),"Reopening started a second connection test");
            Require(FindButton(popup,"‹")!=null,"Could not return to the running test");
            popup.Close();Pump(40);popup.Reveal();Pump(750);
            var viewport=(Control)typeof(Popup).GetField("body",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(popup);
            Require(!popup.IsDisposed&&viewport.Left==popup.Pixels(24),"Interrupted page motion did not settle after close/reopen");
            popup.Dispose();
        }
    }
    static void PageMotion(){
        using(var window=new Form{Location=new Point(40,40),StartPosition=FormStartPosition.Manual,Size=new Size(380,400),ShowInTaskbar=false})
        using(var body=new Panel{Location=new Point(24,94),Size=new Size(332,200)}){
            window.Controls.Add(body);window.Show();var original=window.Bounds;var taller=new Rectangle(original.Left,original.Top-90,original.Width,original.Height+90);
            using(var motion=new TrayPageMotion(window,body,24,()=>body.Height=window.ClientSize.Height-172,()=>false)){
                motion.Start(original,taller,20,true);Require(body.Left==44&&window.Bounds==original,"Page entrance skipped its initial pose");
                var offsets=new List<int>();var heights=new List<int>();Pump(360,()=>{offsets.Add(body.Left-24);heights.Add(window.Height);});
                Require(offsets.Exists(x=>x>0&&x<20)&&offsets.Exists(x=>x<0),"Page content did not spring through intermediate positions");
                Require(heights.Exists(h=>h>original.Height&&h<taller.Height),"Cleanup viewport height snapped instead of animating");
                Require(body.Left==24&&window.Bounds==taller&&!motion.Running,"Page entrance did not settle exactly");
                motion.Start(taller,original,-20,true);Pump(55);int position=motion.Offset;var current=window.Bounds;motion.Pause();motion.Start(current,taller,position,true);
                Require(motion.Offset==position&&window.Bounds==current,"Rapid page reversal jumped to a new pose");Pump(360);
                motion.Start(taller,original,-20,false);Require(window.Bounds==original&&body.Left==24&&!motion.Running,"Reduced motion did not switch immediately");
            }
        }
    }
    sealed class PaintProbe:Control {internal int Frames;protected override void OnPaint(PaintEventArgs e){Frames++;e.Graphics.Clear(Color.MidnightBlue);base.OnPaint(e);}}
    static void AtomicRedraw(){
        using(var window=new Form{Location=new Point(40,40),StartPosition=FormStartPosition.Manual,Size=new Size(220,160),ShowInTaskbar=false,TopMost=true})
        using(var body=new Panel{Bounds=new Rectangle(0,0,180,100)})using(var probe=new PaintProbe{Bounds=new Rectangle(0,0,160,80)}){
            window.Controls.Add(body);window.Show();Pump(30);
            using(var batch=new TrayRedrawBatch(window,body)){body.Controls.Add(probe);probe.CreateControl();probe.Invalidate();window.Invalidate(true);Pump(40);Require(probe.Frames==0,"Rebuilding controls exposed intermediate painted frames");}
            Pump(40);Require(probe.Frames>0&&window.Visible&&body.Visible,"Atomic redraw failed to restore the visible page");
        }
    }
    [STAThread] static int Main(string[] args){
        try{PopupDpi.Enable();Application.EnableVisualStyles();Motion();PageMotion();AtomicRedraw();Dropdown();Appearance();ResponsiveProgress();File.WriteAllText(args[0],"PASS: native opening overshoot, opacity frames, exact settling, close/reopen continuity, reduced motion, dropdown dismissal-click guard, rounded menu sizing, cleanup focus scrolling, scroll reset, inline power selection, 200 progress updates without replacing navigation controls, background navigation, page spring frames, animated height, rapid reversal, reduced page motion, atomic redraw without intermediate paints and outside dismissal. No app actions ran.");return 0;}
        catch(Exception error){File.WriteAllText(args[0],error.ToString());return 1;}
    }
}
}
