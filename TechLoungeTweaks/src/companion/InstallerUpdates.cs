using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace TechLounge {
static class InstallerUpdates {
    const string Repo="https://github.com/RaheemC4/tech-tips/releases/download/";
    const long Limit=1024L*1024*1024;
    static void ValidateUrl(string url){
        var u=new Uri(url);string h=u.Host;
        if(u.Scheme!="https" || !u.IsDefaultPort || u.UserInfo!="" || !(h=="api.github.com"||h=="github.com"||h=="raw.githubusercontent.com"||h=="release-assets.githubusercontent.com"||h=="objects.githubusercontent.com"))throw new IOException("Unexpected update source.");
    }
    static HttpWebResponse Open(string url){
        for(int n=0;n<6;n++){
            ValidateUrl(url);var req=(HttpWebRequest)WebRequest.Create(url);req.UserAgent="TechLoungeTweaks-Companion";req.AllowAutoRedirect=false;req.Timeout=15000;req.ReadWriteTimeout=30000;
            var res=(HttpWebResponse)req.GetResponse();int status=(int)res.StatusCode;
            if(status>=300&&status<400){string next=res.Headers["Location"];res.Dispose();url=new Uri(new Uri(url),next).AbsoluteUri;continue;}
            return res;
        }throw new IOException("Too many update redirects.");
    }
    static Dictionary<string,object> Metadata(string url){using(var res=Open(url))using(var input=res.GetResponseStream())using(var memory=new MemoryStream()){
        Copy(input,memory,4*1024*1024);return Program.Json.Deserialize<Dictionary<string,object>>(System.Text.Encoding.UTF8.GetString(memory.ToArray()));
    }}
    static void Copy(Stream input,Stream output,long limit){var buffer=new byte[65536];long total=0;int n;while((n=input.Read(buffer,0,buffer.Length))>0){total+=n;if(total>limit)throw new IOException("Update exceeds size limit.");output.Write(buffer,0,n);}}
    internal static void VerifyAndExtract(string zip,string expected,string setup){
        using(var sha=SHA256.Create())using(var input=File.OpenRead(zip)){string actual=BitConverter.ToString(sha.ComputeHash(input)).Replace("-","").ToLowerInvariant();if(actual!=expected)throw new IOException("Update checksum mismatch.");}
        using(var archive=ZipFile.OpenRead(zip)){
            var entry=archive.GetEntry("TechLoungeTweaks-Setup.exe");if(entry==null||entry.Length>Limit)throw new IOException("Installer is missing.");
            using(var input=entry.Open())using(var output=File.Create(setup))Copy(input,output,Limit);
        }
    }
    public static bool FullAppRunning(){foreach(var p in Process.GetProcessesByName("TechLoungeTweaks")){using(p){try{if(p.SessionId==Process.GetCurrentProcess().SessionId)return true;}catch{ return true; }}}return false;}
    public static string Run(Tray tray,bool manual,out bool retry){
        retry=false;
        if(tray.Preview)return "Preview: your app is up to date.";
        if(!File.Exists(Path.Combine(Program.Root,"current.txt")))return "Updates are available after installing the app.";
        if(FullAppRunning()){retry=true;return "Updates will install automatically after the full app closes.";}
        ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;
        var manifest=Metadata("https://raw.githubusercontent.com/RaheemC4/tech-tips/main/TechLoungeTweaks/release.json");
        if(!manifest.ContainsKey("distribution")||Convert.ToString(manifest["distribution"])!="installer")return "No installed-app update is available yet.";
        string latest=Convert.ToString(manifest["version"]),current=Path.GetFileName(Program.Here);
        if(!Regex.IsMatch(latest,@"^\d{4}\.\d{2}\.\d{2}\.\d{6}$"))throw new IOException("Invalid update version.");
        if(String.CompareOrdinal(latest,current)<=0)return "Your app is up to date.";
        string url=Convert.ToString(manifest["download_url"]);
        if(!url.StartsWith(Repo,StringComparison.Ordinal))throw new IOException("Unexpected release repository.");
        var files=(Dictionary<string,object>)manifest["files"];
        string expected=Convert.ToString(files["TechLoungeTweaks/TechLoungeTweaks.zip"]);
        if(!Regex.IsMatch(expected,"^[a-f0-9]{64}$"))throw new IOException("Missing update checksum.");
        // Require the independently served GitHub asset digest as well as the
        // repository manifest. Metadata races defer instead of installing.
        var release=Metadata("https://api.github.com/repos/RaheemC4/tech-tips/releases/latest");bool verified=false;
        foreach(var raw in (System.Collections.IEnumerable)release["assets"]){var asset=(Dictionary<string,object>)raw;if(Convert.ToString(asset["browser_download_url"])==url && asset.ContainsKey("digest") && Convert.ToString(asset["digest"])=="sha256:"+expected)verified=true;}
        if(!verified)throw new IOException("Release metadata is not consistent yet.");
        string cache=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"TechLoungeTweaks","UpdateCache",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(cache);
        try {
            string zip=Path.Combine(cache,"update.zip");
            using(var response=Open(url))using(var input=response.GetResponseStream())using(var output=File.Create(zip))Copy(input,output,Limit);
            string setup=Path.Combine(cache,"TechLoungeTweaks-Setup.exe");
            VerifyAndExtract(zip,expected,setup);
            if(FullAppRunning()){retry=true;return "Installation deferred until the full app closes.";}
            using(var install=Process.Start(new ProcessStartInfo(setup,"/S /UPDATE /D="+Program.Root){UseShellExecute=false,CreateNoWindow=true})){
                if(!install.WaitForExit(10*60*1000))return "Installer is still finishing. Check again later.";
                if(install.ExitCode!=0)throw new IOException("Installer did not complete. Current version retained.");
            }
            Program.Start(Path.Combine(Program.Root,"TechLounge.exe"),"--handoff");
            // New tray waits for this instance to release its mutex.
            tray.Post(()=>Application.ExitThread());
            return "Update installed.";
        } finally {try{Directory.Delete(cache,true);}catch(IOException){}catch(UnauthorizedAccessException){}}
    }
}
}
