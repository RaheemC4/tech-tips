using System;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Diagnostics;
// Exercises the real embedded engine. Test roots are unique, never user installs.
class InstallerChecks {
    static int Main(string[] args){
        string root=Path.Combine(Path.GetTempPath(),"TechLoungeNativeCheck-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
        try{
            var assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));var type=assembly.GetType("TechLoungeSetup.Installation",true);
            string cancelled=Path.Combine(root,"cancelled");
            using(var runner=(IDisposable)Activator.CreateInstance(type,new object[]{cancelled,true})){
                var task=Task.Run(()=>Convert.ToInt32(type.GetMethod("Run").Invoke(runner,null)));
                var deadline=DateTime.UtcNow.AddSeconds(60);bool requested=false;
                while(!task.IsCompleted&&DateTime.UtcNow<deadline){
                    int percent=(int)type.GetField("Percent").GetValue(runner);
                    if(percent>=10&&!requested){type.GetMethod("Cancel").Invoke(runner,null);requested=true;}
                    Thread.Sleep(10);
                }
                if(!task.IsCompleted)throw new Exception("Cancellation test timed out.");
                if(!requested||task.Result!=1223||File.Exists(Path.Combine(cancelled,"current.txt")))throw new Exception("Cancelled installation became current or returned success.");
            }
            string blocked=Path.Combine(root,"blocked");File.WriteAllText(blocked,"fixture");
            using(var runner=(IDisposable)Activator.CreateInstance(type,new object[]{blocked,true})){
                var task=Task.Run(()=>Convert.ToInt32(type.GetMethod("Run").Invoke(runner,null)));
                if(!task.Wait(60000))throw new Exception("Invalid-destination test timed out.");
                if(task.Result==0||File.ReadAllText(blocked)!="fixture")throw new Exception("Invalid destination was not rejected safely.");
            }
            string corrupt=Path.Combine(root,"corrupt.exe");File.Copy(args[0],corrupt);
            using(var stream=new FileStream(corrupt,FileMode.Open,FileAccess.ReadWrite)){stream.Position=stream.Length-32;int value=stream.ReadByte();stream.Position--;stream.WriteByte((byte)(value^1));}
            using(var process=Process.Start(new ProcessStartInfo(corrupt,"/S /UPDATE /D="+Path.Combine(root,"corrupt-target")){UseShellExecute=false,CreateNoWindow=true})){
                if(!process.WaitForExit(60000)||process.ExitCode==0||Directory.Exists(Path.Combine(root,"corrupt-target")))throw new Exception("Corrupt payload was executed.");
            }
            File.WriteAllText(args[1],"PASS: real engine cancels before committing a version; invalid destination preserves the existing file; corrupt payload is rejected before engine execution.");return 0;
        }catch(Exception ex){File.WriteAllText(args[1],"FAIL: "+ex+"; test root: "+root);return 1;}
        finally{try{Directory.Delete(root,true);}catch(IOException){}catch(UnauthorizedAccessException){}}
    }
}
