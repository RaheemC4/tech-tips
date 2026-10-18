using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Windows.Forms;
namespace TechLounge {
static class CompanionChecks {
    [STAThread] static int Main(string[] args){
        PopupDpi.Enable();
        try {CheckUpdateBoundaries();CheckButtonPainting();CheckThemeIcons();}catch(Exception ex){File.WriteAllText(args[0],"FAIL: "+ex);return 1;}
        Application.EnableVisualStyles();int code=1;var watch=Stopwatch.StartNew();
        using(var tray=new Tray(false))using(var timer=new Timer{Interval=100}){
            tray.Run("plans",null,false);
            timer.Tick+=(s,e)=>{
                Job job=tray.Jobs["plans"];
                if(job.Running && watch.Elapsed.TotalSeconds<60)return;
                try {
                    if(job.Result==null||!job.Result.ContainsKey("plans"))throw new Exception(job.Message??"No worker result");
                    var plans=(System.Collections.IList)job.Result["plans"];
                    if(plans.Count==0)throw new Exception("No power plans returned");
                    bool active=false;foreach(var raw in plans){var plan=(Dictionary<string,object>)raw;if(Convert.ToBoolean(plan["active"]))active=true;}
                    if(!active)throw new Exception("No active plan returned");
                    var saved=job.Result;
                    for(int n=0;n<4;n++)using(var popup=new Popup(tray)){
                        popup.CreateControl();popup.Render();
                        using(var bitmap=new System.Drawing.Bitmap(popup.Width,popup.Height))popup.DrawToBitmap(bitmap,popup.ClientRectangle);
                    }
                    if(tray.Jobs["plans"].Result!=saved)throw new Exception("Popup disposal lost the completed job");
                    File.WriteAllText(args[0],"PASS: button foreground repaint clears stale pixels and preserves translated clipping; updater rejects untrusted URLs and checksum failures; verified archive extracts only its installer. Packaged worker connected through the restricted pipe and returned "+plans.Count+" real plans, including the active plan. Elapsed: "+watch.Elapsed.TotalSeconds.ToString("F2")+" seconds.");code=0;
                }catch(Exception ex){File.WriteAllText(args[0],"FAIL: "+ex.ToString());}
                timer.Stop();Application.ExitThread();
            };
            timer.Start();Application.Run(tray);
        }return code;
    }
    static Bitmap PaintButton(GlassButton button,Color seed,bool clipped){
        var bitmap=new Bitmap(260,110);
        using(var graphics=Graphics.FromImage(bitmap)){
            graphics.Clear(seed);
            if(clipped){graphics.TranslateTransform(20,10);graphics.SetClip(new Rectangle(5,5,40,30));}
            var paint=typeof(GlassButton).GetMethod("OnPaint",BindingFlags.Instance|BindingFlags.NonPublic);
            // ButtonBase can skip the background callback in native WM_PAINT.
            paint.Invoke(button,new object[]{new PaintEventArgs(graphics,button.ClientRectangle)});
        }
        return bitmap;
    }
    static void CheckButtonPainting(){
        using(var button=new GlassButton{Size=new Size(220,80),Text="Connection\nSpeed & latency",BackColor=Color.FromArgb(24,35,53),Tint=Color.Blue}){
            using(var magenta=PaintButton(button,Color.Magenta,false))using(var lime=PaintButton(button,Color.Lime,false)){
                for(int y=0;y<button.Height;y++)for(int x=0;x<button.Width;x++)
                    if(magenta.GetPixel(x,y)!=lime.GetPixel(x,y))throw new Exception("Button foreground paint depends on stale backing pixels");
            }
            using(var clipped=PaintButton(button,Color.Magenta,true)){
                var expected=new Rectangle(25,15,40,30);bool painted=false;
                for(int y=0;y<clipped.Height;y++)for(int x=0;x<clipped.Width;x++){
                    bool changed=clipped.GetPixel(x,y).ToArgb()!=Color.Magenta.ToArgb();
                    if(changed&&!expected.Contains(x,y))throw new Exception("Button paint escaped its translated clip");
                    painted|=changed;
                }
                if(!painted)throw new Exception("Clipped button did not paint its visible area");
            }
        }
    }
    static void CheckThemeIcons(){
        foreach(string hex in new[]{"#2f7dff","#5865f2","#8b5cf6","#ff2d6b","#16c98a","#12b6cf"}){
            var accent=ColorTranslator.FromHtml(hex);
            using(var icon=TrayGlyph.Create(accent,true,false))using(var bitmap=icon.ToBitmap()){
                if(bitmap.GetPixel(4,16).ToArgb()!=accent.ToArgb())throw new Exception("Active tray icon did not retain theme colour "+hex);
            }
        }
        using(var tray=new Tray(true))using(var popup=new Popup(tray)){
            int expectedWidth=Math.Min((int)Math.Round(380*PopupDpi.PointerScale()),Screen.FromPoint(Cursor.Position).WorkingArea.Width-(int)Math.Round(28*PopupDpi.PointerScale()));
            if(popup.ClientSize.Width!=expectedWidth)throw new Exception("Popup physical width does not match the pointer monitor DPI");
            if(popup.AutoScaleMode!=AutoScaleMode.None)throw new Exception("Manual popup dimensions must not be scaled twice");
        }
    }
    static void CheckUpdateBoundaries(){
        var validate=typeof(InstallerUpdates).GetMethod("ValidateUrl",BindingFlags.NonPublic|BindingFlags.Static);
        foreach(string bad in new[]{"http://github.com/file","https://github.com.evil.test/file","https://user:pass@github.com/file","https://github.com:123/file"}){
            bool rejected=false;try{validate.Invoke(null,new object[]{bad});}catch(TargetInvocationException e){rejected=e.InnerException is IOException;}
            if(!rejected)throw new Exception("Unsafe update URL accepted");
        }
        validate.Invoke(null,new object[]{"https://release-assets.githubusercontent.com/file"});
        string folder=Path.Combine(Path.GetTempPath(),"TLT-check-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);
        try{
            string zip=Path.Combine(folder,"fixture.zip"),setup=Path.Combine(folder,"setup.exe");
            using(var archive=ZipFile.Open(zip,ZipArchiveMode.Create)){
                using(var writer=new StreamWriter(archive.CreateEntry("TechLoungeTweaks-Setup.exe").Open()))writer.Write("fixture installer");
                using(var writer=new StreamWriter(archive.CreateEntry("../escape.txt").Open()))writer.Write("ignored");
            }
            bool rejected=false;try{InstallerUpdates.VerifyAndExtract(zip,new string('0',64),setup);}catch(IOException){rejected=true;}
            if(!rejected||File.Exists(setup))throw new Exception("Checksum failure extracted a file");
            string hash;using(var sha=SHA256.Create())using(var input=File.OpenRead(zip))hash=BitConverter.ToString(sha.ComputeHash(input)).Replace("-","").ToLowerInvariant();
            InstallerUpdates.VerifyAndExtract(zip,hash,setup);
            if(File.ReadAllText(setup)!="fixture installer"||Directory.GetFiles(folder).Length!=2)throw new Exception("Unexpected extraction contents");
        }finally{Directory.Delete(folder,true);}
    }
}
}
