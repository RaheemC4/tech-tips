using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Windows.Forms;
namespace TechLounge {
static class CompanionChecks {
    [STAThread] static int Main(string[] args){
        try {CheckUpdateBoundaries();}catch(Exception ex){File.WriteAllText(args[0],"FAIL: "+ex);return 1;}
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
                    File.WriteAllText(args[0],"PASS: updater rejects untrusted URLs and checksum failures; verified archive extracts only its installer. Packaged worker connected through the restricted pipe and returned "+plans.Count+" real plans, including the active plan. Elapsed: "+watch.Elapsed.TotalSeconds.ToString("F2")+" seconds.");code=0;
                }catch(Exception ex){File.WriteAllText(args[0],"FAIL: "+ex.ToString());}
                timer.Stop();Application.ExitThread();
            };
            timer.Start();Application.Run(tray);
        }return code;
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
