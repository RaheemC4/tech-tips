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
                Require(review!=null&&review.Bottom<=viewport.Height,"Review cleanup still required scrolling");Capture(popup,"tray-result.png");
                var current=new Dictionary<string,object>{{"name","NVIDIA GeForce RTX 5090"},{"installed","617.42"},{"latest","617.42"},{"status","current"}};
                var unknown=new Dictionary<string,object>{{"name","Intel UHD Graphics 770"},{"installed","32.0.101.7088"},{"latest",null},{"status","unknown"}};
                tray.Jobs["drivers"]=new Job{Result=new Dictionary<string,object>{{"gpus",new object[]{current,unknown}}}};
                typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"drivers");popup.Render();
                int cards=0;bool unknownLabel=false;foreach(Control c in viewport.Controls)if(c is TrayGpuCard){var card=(TrayGpuCard)c;cards++;Require(card.Green,"Current or unknown GPU status lost its requested green treatment");unknownLabel|=card.StatusText=="Unknown";}
                Require(cards==2&&unknownLabel,"Driver cards lost a GPU or misrepresented unknown status");Capture(popup,"tray-drivers.png");
                Require(FindButton(popup,"Check again").Bottom<=viewport.Height,"Two GPU cards pushed Check again out of view");
                Require(Popup.FontFor(10,true).Bold||Popup.FontFor(10,true).Name.Contains("Semibold"),"Tray emphasis lost its semibold weight");
                tray.Window=popup;tray.SetUpdateAvailable(true);Require(FindButton(popup,"● Update available")==null,"Update indicator appeared outside Quick actions");
                typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"home");popup.Render();
                Require(FindButton(popup,"● Update available")!=null,"Available update lacked its compact indicator");Capture(popup,"tray-update-indicator.png");
                tray.SetUpdateAvailable(false);Require(FindButton(popup,"● Update available")==null&&FindButton(popup,"Updates")==null,"Tray retained a redundant update control");
                Require(FindButton(popup,"Open app").Width==popup.ClientSize.Width-popup.Pixels(48),"Normal footer retained the empty update column");Capture(popup,"companion.png");
                popup.Dispose();
            }
        }
    }
    static void Capture(Popup popup,string name){
        string directory=Environment.GetEnvironmentVariable("TLT_TRAY_FIXTURES");if(string.IsNullOrEmpty(directory))return;popup.Activate();popup.Refresh();Pump(420);using(var bitmap=new Bitmap(popup.Width,popup.Height,System.Drawing.Imaging.PixelFormat.Format24bppRgb)){using(var graphics=Graphics.FromImage(bitmap))graphics.CopyFromScreen(popup.Location,Point.Empty,popup.Size);bitmap.Save(Path.Combine(directory,name));}
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
    static void CleanupFooter(){
        using(var tray=new Tray(true))using(var popup=new Popup(tray)){
            tray.Window=popup;popup.Show();Pump(420);
            var page=typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
            var body=(TrayScrollPanel)typeof(Popup).GetField("body",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(popup);
            Action verify=()=>{
                var clean=FindButton(popup,"Clean selected");var open=FindButton(popup,"Open app");
                Require(clean!=null&&open!=null,"Cleanup footer changed its button count while loading");
                Require(!clean.Bounds.IntersectsWith(open.Bounds),"Cleanup footer buttons overlapped");
                Require(open.Left-clean.Right==popup.Pixels(12),"Cleanup footer gap changed during animation");
                Require(Math.Abs(clean.Width-open.Width)<=1&&clean.Top==open.Top&&clean.Height==open.Height,"Cleanup footer buttons lost equal sizing/alignment");
                Require(body.Bottom<=clean.Top-popup.Pixels(16),"Cleanup rows overlapped the footer");
                Require(open.Right<=popup.ClientSize.Width-popup.Pixels(24)&&open.Bottom<=popup.ClientSize.Height-popup.Pixels(24),"Footer left the popup bounds");
                Require(((GlassButton)clean).Primary&&!((GlassButton)open).Primary,"Cleanup footer did not distinguish primary/secondary actions");
            };
            tray.Jobs["scan"]=new Job{Running=true,Message="Scanning disk"};page.SetValue(popup,"scan");popup.Render();
            Pump(350,verify);Require(!FindButton(popup,"Clean selected").Enabled,"Cleanup was enabled before scan results");
            var names=new[]{"Your temp files","Windows temp files","Windows Update cache","Delivery Optimization","Crash dumps","Thumbnail cache","Windows error reports","Prefetch data","Recycle Bin"};
            var sizes=new[]{"285.2 MB","116 B","0 B","1.5 MB","0 B","0 B","0 B","0 B","3.2 MB"};
            var entries=new List<object>();for(int i=0;i<names.Length;i++)entries.Add(new Dictionary<string,object>{{"id","fixture"+i},{"name",names[i]},{"human",sizes[i]},{"default",i<7}});
            tray.Jobs["scan"]=new Job{Result=new Dictionary<string,object>{{"items",entries.ToArray()}}};popup.Render();Pump(80,verify);
            Require(FindButton(popup,"Clean selected").Enabled,"Cleanup did not enable after a selected result");
            foreach(Control c in body.Controls)if(c is CheckBox)((CheckBox)c).Checked=false;
            Require(!FindButton(popup,"Clean selected").Enabled,"Empty cleanup selection remained actionable");
            foreach(Control c in body.Controls)if(c is CheckBox){((CheckBox)c).Checked=true;break;}
            Require(FindButton(popup,"Clean selected").Enabled,"Re-selecting a category did not restore cleanup");
            page.SetValue(popup,"home");popup.Render();Pump(55);page.SetValue(popup,"scan");popup.Render();Pump(350,verify);
            string screenshot=Environment.GetEnvironmentVariable("TLT_POPUP_SCREENSHOT");
            if(!string.IsNullOrEmpty(screenshot))using(var bitmap=new Bitmap(popup.Width,popup.Height,System.Drawing.Imaging.PixelFormat.Format24bppRgb)){
                popup.Activate();popup.Refresh();Pump(40);using(var graphics=Graphics.FromImage(bitmap))graphics.CopyFromScreen(popup.Location,Point.Empty,popup.Size);bitmap.Save(screenshot);
            }
            popup.Dispose();
        }
    }
    sealed class ResizeProbe:NativeWindow,IDisposable {
        internal int Sizes;internal bool Copied;
        internal ResizeProbe(Control window){AssignHandle(window.Handle);}
        protected override void WndProc(ref Message message){
            if(message.Msg==0x47&&message.LParam!=IntPtr.Zero){var position=(TrayGeometry.WindowPosition)System.Runtime.InteropServices.Marshal.PtrToStructure(message.LParam,typeof(TrayGeometry.WindowPosition));if((position.Flags&1)==0){Sizes++;Copied|=(position.Flags&0x100)==0;}}
            base.WndProc(ref message);
        }
        public void Dispose(){ReleaseHandle();}
    }
    static void TransitionPixels(){
        using(var tray=new Tray(true))using(var popup=new Popup(tray)){
            tray.Window=popup;
            tray.Jobs["scan"]=new Job{Result=new Dictionary<string,object>{{"items",new object[]{new Dictionary<string,object>{{"id","fixture"},{"name","Your temp files"},{"human","225 MB"},{"default",true}}}}}};
            tray.Jobs["connection"]=new Job{Running=true,Message="Testing download"};
            var page=typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
            // A scan rendered before Show must use the same split layout.
            page.SetValue(popup,"scan");popup.Render();popup.Show();Pump(420);
            var original=FindButton(popup,"Open app");IntPtr handle=original.Handle;
            Require(!original.Bounds.IntersectsWith(FindButton(popup,"Clean selected").Bounds),"Hidden-to-visible cleanup overlapped its footer");
            var stableBounds=popup.Bounds;int stableFooterTop=original.Top;
            using(var resize=new ResizeProbe(popup)){
            foreach(string route in new[]{"scan","home","connection","scan","settings","drivers","scan","home"}){
                page.SetValue(popup,route);popup.Render();Pump(340,()=>{Require(popup.Bounds==stableBounds&&original.Top==stableFooterTop,"Navigation moved the popup/footer during "+route);});
                Require(object.ReferenceEquals(original,FindButton(popup,"Open app"))&&original.Handle==handle,"Navigation recreated the footer HWND");
                Require(popup.Controls.Count==6,"Navigation duplicated native header/footer controls");
                using(var actual=new Bitmap(popup.Width,popup.Height,System.Drawing.Imaging.PixelFormat.Format24bppRgb))
                using(var expected=new Bitmap(popup.Width,popup.Height,System.Drawing.Imaging.PixelFormat.Format24bppRgb)){
                    using(var graphics=Graphics.FromImage(actual))graphics.CopyFromScreen(popup.Location,Point.Empty,popup.Size);
                    popup.DrawToBitmap(expected,popup.ClientRectangle);
                    long error=0;int count=0;
                    for(int y=popup.ClientSize.Height-popup.Pixels(74);y<popup.ClientSize.Height-popup.Pixels(20);y+=2)for(int x=popup.Pixels(22);x<popup.ClientSize.Width-popup.Pixels(22);x+=2){var a=actual.GetPixel(x,y);var b=expected.GetPixel(x,y);error+=Math.Abs(a.R-b.R)+Math.Abs(a.G-b.G)+Math.Abs(a.B-b.B);count+=3;}
                    long bodyError=0;int bodyCount=0;
                    for(int y=popup.Pixels(94);y<popup.ClientSize.Height-popup.Pixels(80);y+=4)for(int x=popup.Pixels(24);x<popup.ClientSize.Width-popup.Pixels(24);x+=4){var a=actual.GetPixel(x,y);var b=expected.GetPixel(x,y);bodyError+=Math.Abs(a.R-b.R)+Math.Abs(a.G-b.G)+Math.Abs(a.B-b.B);bodyCount+=3;}
                    Require((double)bodyError/bodyCount<.3,"Native page retained old pixels during "+route+": "+((double)bodyError/bodyCount).ToString("F3"));
                    Require((double)error/count<.2,"Native footer retained old pixels during "+route+": "+((double)error/count).ToString("F3"));
                }
                // Late background messages must not recreate the chrome either.
                if(route=="connection"){tray.Jobs["connection"].Running=false;tray.Jobs["connection"].Message="Test complete. Download 1684 Mbps.";}
                tray.RefreshJob("connection");Require(original.Handle==handle,"Background result recreated the footer");
            }
            Require(resize.Sizes==0,"Page navigation resized the native popup");}
            tray.Accent=Color.MediumPurple;popup.Render();Require(((GlassButton)original).Tint==tray.Accent,"Persistent footer lost selected theme tint");
            popup.Dispose();
        }
    }
    static void ConnectionResults(){
        Require(TrayMetricCard.Number(0,true)=="Unavailable"&&TrayMetricCard.Number(null,true)=="Unavailable"&&TrayMetricCard.Number(double.NaN,false)=="Unavailable","Invalid speed became a measured result");
        Require(TrayMetricCard.Number(119.48,true)==119.5.ToString("0.0")&&TrayMetricCard.Number(7.43,false)==7.43.ToString("0.##"),"Metric precision changed");
        using(var tray=new Tray(true))using(var popup=new Popup(tray)){
            tray.Window=popup;tray.Jobs["connection"]=new Job{Result=new Dictionary<string,object>{{"download_mbps",0.0},{"upload_mbps",119.48},{"idle_ms",7.43},{"grade","A+"}}};
            typeof(Popup).GetField("page",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(popup,"connection");popup.Render();popup.Show();Pump(420);
            var body=(TrayScrollPanel)typeof(Popup).GetField("body",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(popup);int cards=0;
            foreach(Control control in body.Controls){Require(control.Bottom<=body.Height,"Connection results require scrolling");var card=control as TrayMetricCard;if(card==null)continue;cards++;if(card.AccessibleName.StartsWith("Download"))Require(card.Caption=="Not measured","Zero download shown as success");if(card.AccessibleName.StartsWith("Bufferbloat"))Require(card.Value=="A+"&&card.StatusColor==Color.FromArgb(61,220,151),"A+ lost green status");}
            Require(cards==4&&FindButton(popup,"Test again")!=null,"Connection metrics/retry missing");
            string screenshot=Environment.GetEnvironmentVariable("TLT_CONNECTION_SCREENSHOT");if(!string.IsNullOrEmpty(screenshot))using(var bitmap=new Bitmap(popup.Width,popup.Height,System.Drawing.Imaging.PixelFormat.Format24bppRgb)){popup.Activate();popup.Refresh();Pump(40);using(var graphics=Graphics.FromImage(bitmap))graphics.CopyFromScreen(popup.Location,Point.Empty,popup.Size);bitmap.Save(screenshot);}
            popup.Dispose();
        }
    }
    [STAThread] static int Main(string[] args){
        try{PopupDpi.Enable();Application.EnableVisualStyles();Motion();PageMotion();AtomicRedraw();Dropdown();Appearance();CleanupFooter();TransitionPixels();ResponsiveProgress();ConnectionResults();File.WriteAllText(args[0],"PASS: native opening overshoot, opacity frames, exact settling, close/reopen continuity, reduced motion, dropdown dismissal-click guard, rounded menu sizing, cleanup focus scrolling, stable non-overlapping footer through loading and animated reversal, selection enablement, scroll reset, inline power selection, 200 progress updates without replacing navigation controls, background navigation, page spring frames, animated height, rapid reversal, reduced page motion, atomic redraw without intermediate paints, persistent chrome HWNDs, native footer/page pixel comparisons during rapid navigation, fixed popup and footer geometry throughout every navigation frame, theme updates and outside dismissal. No app actions ran.");return 0;}
        catch(Exception error){File.WriteAllText(args[0],error.ToString());return 1;}
    }
}
}
