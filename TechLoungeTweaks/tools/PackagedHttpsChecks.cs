using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

static class PackagedHttpsChecks {
    static int Main(string[] args) {
        Process worker=null;
        try {
            if(args.Length!=2)throw new ArgumentException("Expected packaged executable and report path.");
            var json=new JavaScriptSerializer();
            var security=new PipeSecurity();
            var user=WindowsIdentity.GetCurrent().User;
            security.AddAccessRule(new PipeAccessRule(user,PipeAccessRights.FullControl,AccessControlType.Allow));
            string name="TLT-"+Guid.NewGuid().ToString("N");
            using(var pipe=new NamedPipeServerStream(name,PipeDirection.In,1,PipeTransmissionMode.Byte,PipeOptions.Asynchronous,4096,4096,security)) {
                string payload=Convert.ToBase64String(Encoding.UTF8.GetBytes(json.Serialize(new {value=(string)null,user_sid=user.Value})));
                worker=Process.Start(new ProcessStartInfo(Path.GetFullPath(args[0]),"--companion-worker "+name+" https-probe "+payload){UseShellExecute=false,CreateNoWindow=true});
                var connection=Task.Factory.FromAsync(pipe.BeginWaitForConnection,pipe.EndWaitForConnection,null);
                if(!connection.Wait(30000))throw new TimeoutException("Packaged HTTPS worker did not connect.");
                using(var reader=new StreamReader(pipe,Encoding.UTF8)) {
                    var reading=reader.ReadLineAsync();
                    if(!reading.Wait(30000))throw new TimeoutException("Packaged HTTPS worker did not return a result.");
                    var message=json.Deserialize<Dictionary<string,object>>(reading.Result??"");
                    var data=message["data"] as Dictionary<string,object>;
                    if(!message.ContainsKey("done")||data==null||!data.ContainsKey("ok")||!Convert.ToBoolean(data["ok"]))
                        throw new IOException("Packaged HTTPS failed: "+json.Serialize(data));
                    int count=Convert.ToInt32(data["bytes_received"]),status=Convert.ToInt32(data["status"]);
                    if(!Convert.ToBoolean(data["certificate_verification"])||count<1||count>65536||(status!=200&&status!=206))
                        throw new IOException("Packaged worker did not verify HTTPS and receive bounded bytes.");
                    if(!worker.WaitForExit(5000)||worker.ExitCode!=0)throw new IOException("Packaged worker failed after reporting.");
                    File.WriteAllText(args[1],json.Serialize(data));
                    Console.WriteLine("PASS: frozen worker returned "+count+" HTTPS bytes, HTTP "+status+", certificate and hostname checks enabled, through its named pipe.");
                }
            }
            return 0;
        } catch(Exception error) {
            Console.Error.WriteLine(error);
            if(args.Length==2)File.WriteAllText(args[1],error.ToString());
            return 1;
        } finally {
            // Only the exact child started by this finite check may be stopped.
            if(worker!=null){try{if(!worker.HasExited)worker.Kill();}catch(InvalidOperationException){}worker.Dispose();}
        }
    }
}
