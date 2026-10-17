using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

namespace TechLounge {
static class Program {
    public static readonly string Sid = WindowsIdentity.GetCurrent().User.Value;
    public static readonly string Here = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
    public static JavaScriptSerializer Json {get{return new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };}}
    public static string Root { get { return Directory.Exists(Path.Combine(Here,"versions")) ? Here : Directory.GetParent(Here).Parent.FullName; } }
    public static string Current {
        get {
            string value=File.ReadAllText(Path.Combine(Root,"current.txt")).Trim();
            if(!Regex.IsMatch(value,@"^\d{4}\.\d{2}\.\d{2}\.\d{6}$")) throw new IOException("Invalid installation version.");
            return Path.Combine(Root,"versions",value);
        }
    }
    public static string TaskName { get {return "TechLoungeTweaks-"+Sid;} }
    public static RegistryKey Settings { get {return Registry.CurrentUser.CreateSubKey(@"Software\TechLoungeTweaks");} }
    public static string Setting(string key,string fallback) {using(var r=Settings)return Convert.ToString(r.GetValue(key,fallback));}
    public static void Save(string key,string value) {using(var r=Settings)r.SetValue(key,value);}
    public static void Start(string path,string args) {Process.Start(new ProcessStartInfo(path,args){UseShellExecute=true,WorkingDirectory=Path.GetDirectoryName(path)});}
    public static void Startup(bool enabled) {
        dynamic scheduler=Activator.CreateInstance(Type.GetTypeFromProgID("Schedule.Service")); scheduler.Connect();
        dynamic folder=scheduler.GetFolder("\\");
        if(!enabled) {try{folder.DeleteTask(TaskName,0);}catch(FileNotFoundException){}catch(System.Runtime.InteropServices.COMException ex){if(ex.HResult!=unchecked((int)0x80070002))throw;} Save("Startup","0");return;}
        dynamic task=scheduler.NewTask(0);
        task.RegistrationInfo.Description="Tech Lounge tray companion. Starts three minutes after sign-in.";
        task.Principal.UserId=Sid; task.Principal.LogonType=3; task.Principal.RunLevel=0;
        task.Settings.DisallowStartIfOnBatteries=false; task.Settings.StopIfGoingOnBatteries=false;
        task.Settings.ExecutionTimeLimit="PT0S"; task.Settings.MultipleInstances=2;
        dynamic trigger=task.Triggers.Create(9); trigger.UserId=Sid; trigger.Delay="PT3M";
        dynamic action=task.Actions.Create(0); action.Path=Path.Combine(Root,"TechLounge.exe"); action.Arguments="--tray";
        folder.RegisterTaskDefinition(TaskName,task,6,Sid,null,3,null); Save("Startup","1");
    }
    [STAThread] static int Main(string[] args) {
        try {
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            string mode=args.Length==0?"--open":args[0];
            if(mode=="--install") {if(Setting("Startup","1")=="1")Startup(true);PruneVersions();return 0;}
            if(mode=="--prepare-install") {if(InstallerUpdates.FullAppRunning())return 1;Stop();return 0;}
            if(mode=="--uninstall") {
                if(InstallerUpdates.FullAppRunning())throw new IOException("Close Tech Lounge Tweaks and finish quick actions before uninstalling.");
                Startup(false);Stop();return 0;
            }
            if(mode=="--stop") {Stop();return 0;}
            if(mode=="--preview") {
                using(var tray=new Tray(true))using(var popup=new Popup(tray)){
                    popup.Show();Application.DoEvents();
                    using(var bitmap=new Bitmap(popup.Width,popup.Height)){popup.DrawToBitmap(bitmap,popup.ClientRectangle);bitmap.Save(args[1]);}
                }return 0;
            }
            if(!File.Exists(Path.Combine(Here,"TechLoungeTweaks.exe"))) {
                Start(Path.Combine(Current,"TechLounge.exe"),mode=="--handoff"?"--handoff":"--tray");
                if(mode!="--tray"&&mode!="--handoff")Start(Path.Combine(Current,"TechLoungeTweaks.exe"),"");
                return 0;
            }
            if(mode!="--tray"&&mode!="--handoff")Start(Path.Combine(Here,"TechLoungeTweaks.exe"),"");
            bool owner;
            using(var single=new Mutex(true,"Local\\TechLoungeTray-"+Sid,out owner)) {
                if(!owner){
                    if(mode!="--handoff")return 0;
                    try{owner=single.WaitOne(15000);}catch(AbandonedMutexException){owner=true;}
                    if(!owner)return 0;
                }
                try{using(var tray=new Tray(false))Application.Run(tray);}
                finally{single.ReleaseMutex();}
            }
            return 0;
        } catch(Exception ex) {
            if(args.Length==0 || args[0]=="--open")MessageBox.Show(ex.Message,"Tech Lounge",MessageBoxButtons.OK,MessageBoxIcon.Information);
            try{Save("LastError",ex.Message);}catch{}
            return 1;
        }
    }
    static void Stop(){try{using(var e=EventWaitHandle.OpenExisting("Local\\TechLoungeQuit-"+Sid))e.Set();}catch(WaitHandleCannotBeOpenedException){}}
    static void PruneVersions(){
        if(InstallerUpdates.FullAppRunning())return;
        string current=Current;var versions=new List<string>();var active=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if((File.GetAttributes(Path.Combine(Root,"versions"))&FileAttributes.ReparsePoint)!=0)return;
        foreach(var process in Process.GetProcessesByName("TechLounge"))using(process){try{active.Add(Path.GetDirectoryName(process.MainModule.FileName));}catch{return;}}
        foreach(string dir in Directory.GetDirectories(Path.Combine(Root,"versions")))if(Regex.IsMatch(Path.GetFileName(dir),@"^\d{4}\.\d{2}\.\d{2}\.\d{6}$"))versions.Add(dir);
        versions.Sort(StringComparer.Ordinal);versions.Reverse();
        for(int i=2;i<versions.Count;i++){
            string path=Path.GetFullPath(versions[i]);
            if(path==current||active.Contains(path)||!path.StartsWith(Path.GetFullPath(Path.Combine(Root,"versions"))+"\\",StringComparison.OrdinalIgnoreCase))continue;
            try{
                bool safe=true;var queue=new Stack<string>();queue.Push(path);
                while(queue.Count>0){string dir=queue.Pop();if((File.GetAttributes(dir)&FileAttributes.ReparsePoint)!=0){safe=false;break;}foreach(string child in Directory.GetDirectories(dir))queue.Push(child);}
                if(safe)Directory.Delete(path,true);
            }catch(IOException){}catch(UnauthorizedAccessException){}
        }
    }
}

sealed class Job {public bool Running;public string Message;public Dictionary<string,object> Result;}
sealed class Tray : ApplicationContext {
    public readonly Dictionary<string,Job> Jobs=new Dictionary<string,Job>();
    public bool Preview; public Popup Window; public Color Accent;
    readonly NotifyIcon icon; readonly Control dispatch=new Control();
    readonly EventWaitHandle quit; readonly RegisteredWaitHandle quitWait;
    readonly System.Threading.Timer updateTimer;
    bool disposed; public bool Updating;
    public Tray(bool preview) {
        Preview=preview; LoadTheme(); dispatch.CreateControl();
        if(preview) {Jobs["plans"]=new Job{Result=new Dictionary<string,object>{{"plans",new object[]{new Dictionary<string,object>{{"id","balanced"},{"name","Balanced"},{"active",true}}}}}};return;}
        icon=new NotifyIcon{Text="Tech Lounge Tweaks",Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath),Visible=true};
        icon.MouseClick+=(s,e)=>{if(e.Button==MouseButtons.Left)ShowPopup();};
        var menu=new ContextMenuStrip();
        menu.Items.Add("Quick actions",null,(s,e)=>ShowPopup());
        menu.Items.Add("Open app",null,(s,e)=>OpenApp());
        menu.Items.Add("Exit companion",null,(s,e)=>{if(Busy){ShowPopup();return;}ExitThread();});
        icon.ContextMenuStrip=menu;
        quit=new EventWaitHandle(false,EventResetMode.AutoReset,"Local\\TechLoungeQuit-"+Program.Sid);
        quitWait=ThreadPool.RegisterWaitForSingleObject(quit,(s,t)=>Post(()=>ExitThread()),null,-1,true);
        // Nothing checks the network at sign-in. Two checks per day after a
        // fifteen-minute grace period; the timer consumes no CPU while waiting.
        updateTimer=new System.Threading.Timer(s=>CheckUpdates(false),null,TimeSpan.FromMinutes(15),System.Threading.Timeout.InfiniteTimeSpan);
    }
    public bool Busy {get {foreach(var j in Jobs.Values)if(j.Running)return true;return Updating;}}
    public void LoadTheme(){
        var colors=new Dictionary<string,string>{{"blue","#2f7dff"},{"blurple","#5865f2"},{"purple","#8b5cf6"},{"red","#ff2d6b"},{"green","#16c98a"},{"cyan","#12b6cf"}};
        string name=Program.Setting("Theme","blue"); Accent=ColorTranslator.FromHtml(colors.ContainsKey(name)?colors[name]:colors["blue"]);
    }
    public void Post(Action action){if(!disposed && dispatch.IsHandleCreated)try{dispatch.BeginInvoke(action);}catch(InvalidOperationException){}}
    public void Refresh(){if(Window!=null && !Window.IsDisposed)Window.Render();}
    public void ShowPopup(){
        LoadTheme(); if(Window!=null && !Window.IsDisposed){Window.Activate();return;}
        Window=new Popup(this);Window.Show();Window.Activate();
        Run("plans",null,false);
    }
    public void OpenApp(){try{Program.Start(Path.Combine(Program.Here,"TechLoungeTweaks.exe"),"");if(Window!=null)Window.Close();}catch(Exception ex){Jobs["open"]=new Job{Message=ex.Message};Refresh();}}
    public void Run(string action,object payload,bool elevate) {
        Job existing;if(Jobs.TryGetValue(action,out existing)&&existing.Running)return;
        if(Updating){Jobs[action]=new Job{Message="The updater is busy. Try again shortly."};Refresh();return;}
        var job=new Job{Running=true,Message="Working…",Result=action=="plans"&&existing!=null?existing.Result:null};Jobs[action]=job;Refresh();
        Task.Run(async()=>{
            try {
                if(Preview){await Task.Delay(1200);Post(()=>{job.Running=false;job.Message="Preview complete.";Refresh();});return;}
                var security=new PipeSecurity();
                security.AddAccessRule(new PipeAccessRule(WindowsIdentity.GetCurrent().User,PipeAccessRights.FullControl,AccessControlType.Allow));
                security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid,null),PipeAccessRights.ReadWrite,AccessControlType.Allow));
                string name="TLT-"+Guid.NewGuid().ToString("N");
                using(var pipe=new NamedPipeServerStream(name,PipeDirection.In,1,PipeTransmissionMode.Byte,PipeOptions.Asynchronous,4096,4096,security)) {
                    string encoded=Convert.ToBase64String(Encoding.UTF8.GetBytes(Program.Json.Serialize(new Dictionary<string,object>{{"value",payload},{"user_sid",Program.Sid}})));
                    var start=new ProcessStartInfo(Path.Combine(Program.Here,"TechLoungeTweaks.exe"),"--companion-worker "+name+" "+action+" "+encoded){UseShellExecute=true,WindowStyle=ProcessWindowStyle.Hidden};
                    if(elevate)start.Verb="runas";
                    using(var process=Process.Start(start)) {
                        var connect=Task.Factory.FromAsync(pipe.BeginWaitForConnection,pipe.EndWaitForConnection,null);
                        if(await Task.WhenAny(connect,Task.Delay(90000))!=connect)throw new TimeoutException("The action did not start. You can retry.");
                        await connect;
                        using(var reader=new StreamReader(pipe,Encoding.UTF8)) {
                            while(true){
                                // Keep an active job owned until its worker finishes. A slow
                                // cleanup must not time out and allow a duplicate cleanup.
                                string line=await reader.ReadLineAsync();if(line==null)throw new IOException("The action ended without a result.");
                                if(line.Length>1024*1024)throw new IOException("Action result too large.");
                                var message=Program.Json.Deserialize<Dictionary<string,object>>(line);
                                var data=message["data"] as Dictionary<string,object>;
                                if(message.ContainsKey("done")) {Post(()=>{job.Result=data;job.Running=false;job.Message=Describe(action,data);if(action=="power"&&data.ContainsKey("plans"))Jobs["plans"]=job;Refresh();});break;}
                                if(data!=null&&data.ContainsKey("label")) {string label=Convert.ToString(data["label"]);Post(()=>{job.Message=label;Refresh();});}
                            }
                        }
                    }
                }
            }catch(Exception ex){Post(()=>{job.Running=false;job.Message=ex is System.ComponentModel.Win32Exception?"Action cancelled or Windows permission was denied.":ex.Message;Refresh();});}
        });
    }
    static string Describe(string action,Dictionary<string,object> data){
        foreach(string key in new[]{"error","__error__","message"})if(data.ContainsKey(key))return Convert.ToString(data[key]);
        if(action=="clean")return "Freed "+data["freed"]+". Skipped "+data["skipped"]+" files in use or protected by Windows.";
        if(action=="connection")return "Download  "+Get(data,"download_mbps")+" Mbps\nUpload  "+Get(data,"upload_mbps")+" Mbps\nLatency  "+Get(data,"idle_ms")+" ms\nGrade  "+Get(data,"grade");
        if(action=="drivers"){
            var result=new StringBuilder();foreach(var item in (System.Collections.IEnumerable)data["gpus"]){var gpu=(Dictionary<string,object>)item;result.AppendLine(Get(gpu,"name")+"\nInstalled: "+Get(gpu,"installed")+" · "+Get(gpu,"status"));}return result.Length>0?result.ToString():"No supported GPU detected.";
        }return "Complete.";
    }
    static string Get(Dictionary<string,object> data,string key){return data.ContainsKey(key)?Convert.ToString(data[key]):"Unavailable";}
    public void CheckUpdates(bool manual){Post(()=>{
        if(Busy){if(!Updating){Jobs["updates"]=new Job{Message="Updates will check after the current action finishes."};Refresh();ScheduleUpdate(true);}return;}
        Updating=true;Jobs["updates"]=new Job{Running=true,Message="Checking for updates…"};Refresh();
        Task.Run(()=>{string status;bool retry;try{status=InstallerUpdates.Run(this,manual,out retry);}catch(Exception ex){retry=true;status="Update check unavailable. Will retry later. "+ex.Message;}
            Post(()=>{Updating=false;Jobs["updates"].Running=false;Jobs["updates"].Message=status;Refresh();ScheduleUpdate(retry);});});
    });}
    void ScheduleUpdate(bool retry){if(updateTimer!=null)updateTimer.Change(retry?TimeSpan.FromMinutes(15):TimeSpan.FromHours(12),System.Threading.Timeout.InfiniteTimeSpan);}
    protected override void Dispose(bool disposing){disposed=true;if(disposing){if(updateTimer!=null)updateTimer.Dispose();if(quitWait!=null)quitWait.Unregister(null);if(quit!=null)quit.Dispose();if(icon!=null){icon.Visible=false;icon.Dispose();}if(Window!=null)Window.Dispose();dispatch.Dispose();}base.Dispose(disposing);}
}

sealed class GlassButton:Button {
    public Color Tint; public bool Primary;
    public GlassButton(){FlatStyle=FlatStyle.Flat;FlatAppearance.BorderSize=0;ForeColor=Color.FromArgb(232,238,248);Font=Popup.FontFor(10,true);Cursor=Cursors.Hand;SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer,true);}
    protected override void OnPaint(PaintEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        var box=new Rectangle(0,0,Width-1,Height-1);
        using(var shape=Popup.Round(box,12))using(var fill=new SolidBrush(Primary?Color.FromArgb(210,Tint):Color.FromArgb(Focused||ClientRectangle.Contains(PointToClient(Cursor.Position))?65:32,180,200,235)))e.Graphics.FillPath(fill,shape);
        TextRenderer.DrawText(e.Graphics,Text,Font,box,Enabled?ForeColor:Color.Gray,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.WordBreak|TextFormatFlags.NoPrefix);
        if(Focused)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(box,-5,-5),ForeColor,BackColor);
    }
}
sealed class Popup:Form {
    static readonly Dictionary<string,Font> fonts=new Dictionary<string,Font>();
    internal static Font FontFor(int size,bool bold){string key=size+":"+bold;Font font;if(!fonts.TryGetValue(key,out font)){font=new Font("Segoe UI",size,bold?FontStyle.Bold:FontStyle.Regular);fonts[key]=font;}return font;}
    readonly Tray tray; readonly Panel body=new Panel();string page="home";
    public Popup(Tray owner){
        tray=owner;Text="Tech Lounge quick actions";FormBorderStyle=FormBorderStyle.None;ShowInTaskbar=false;TopMost=true;StartPosition=FormStartPosition.Manual;
        AutoScaleMode=AutoScaleMode.Dpi;ClientSize=new Size(410,600);DoubleBuffered=true;BackColor=Color.FromArgb(24,35,53);ForeColor=Color.FromArgb(232,238,248);Font=FontFor(10,false);KeyPreview=true;
        KeyDown+=(s,e)=>{if(e.KeyCode==Keys.Escape)Close();};
        var area=Screen.FromPoint(Cursor.Position).WorkingArea;ClientSize=new Size(Math.Min(410,area.Width-28),Math.Min(600,area.Height-28));Location=new Point(area.Right-Width-14,area.Bottom-Height-14);
        body.SetBounds(24,106,ClientSize.Width-48,ClientSize.Height-200);body.BackColor=Color.Transparent;body.AutoScroll=true;Controls.Add(body);
        Deactivate+=(s,e)=>{if(!ContainsFocus)Close();};FormClosed+=(s,e)=>{tray.Window=null;};Render();
    }
    public static GraphicsPath Round(Rectangle r,int radius){var p=new GraphicsPath();int d=radius*2;p.AddArc(r.X,r.Y,d,d,180,90);p.AddArc(r.Right-d,r.Y,d,d,270,90);p.AddArc(r.Right-d,r.Bottom-d,d,d,0,90);p.AddArc(r.X,r.Bottom-d,d,d,90,90);p.CloseFigure();return p;}
    protected override void OnPaint(PaintEventArgs e){
        base.OnPaint(e);e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var b=new LinearGradientBrush(ClientRectangle,Color.FromArgb(28+tray.Accent.R/5,35+tray.Accent.G/5,48+tray.Accent.B/5),Color.FromArgb(23,34,53),45))e.Graphics.FillRectangle(b,ClientRectangle);
    }
    protected override void OnResize(EventArgs e){base.OnResize(e);if(Width>0&&Height>0)using(var p=Round(ClientRectangle,24)){var old=Region;Region=new Region(p);if(old!=null)old.Dispose();}}
    Label Label(string text,int x,int y,int width,int height,int size,bool bold,Control parent){var l=new Label{Text=text,BackColor=Color.Transparent,ForeColor=ForeColor,Font=FontFor(size,bold)};l.SetBounds(x,y,width,height);parent.Controls.Add(l);return l;}
    GlassButton Button(string text,int x,int y,int w,int h,Action click,Control parent,bool primary=false){var b=new GlassButton{Text=text,Tint=tray.Accent,Primary=primary,BackColor=BackColor};b.SetBounds(x,y,w,h);b.Click+=(s,e)=>click();parent.Controls.Add(b);return b;}
    public void Render(){
        SuspendLayout();foreach(Control c in new List<Control>(Children(this)))if(c!=body){Controls.Remove(c);c.Dispose();}
        foreach(Control c in Children(body))c.Dispose();body.Controls.Clear();
        Label("Tech Lounge",24,24,270,32,19,true,this);Label("A little control. Right here.",24,61,290,25,10,false,this);
        Button("⚙",ClientSize.Width-72,28,48,43,()=>{page="settings";Render();},this).AccessibleName="Companion settings";
        int footerWidth=(ClientSize.Width-60)/2;
        Button("Updates",24,ClientSize.Height-66,footerWidth,44,()=>{page="updates";tray.CheckUpdates(true);Render();},this);
        Button("Open app",36+footerWidth,ClientSize.Height-66,footerWidth,44,()=>tray.OpenApp(),this,true);
        if(page=="home")Home();else if(page=="settings")Settings();else Detail();
        ResumeLayout();Invalidate();
    }
    static List<Control> Children(Control parent){var result=new List<Control>();foreach(Control c in parent.Controls)result.Add(c);return result;}
    void Home(){
        Label("Power plan",0,4,360,28,12,true,body);
        var choices=new ContextMenuStrip{BackColor=Color.FromArgb(34,49,72),ForeColor=ForeColor,ShowImageMargin=false,Font=Font,Renderer=new ToolStripProfessionalRenderer(new GlassMenuColors())};
        string active="Loading plans…";bool ultimate=false;Job planJob;
        if(tray.Jobs.TryGetValue("plans",out planJob)&&planJob.Result!=null&&planJob.Result.ContainsKey("plans"))foreach(var raw in (System.Collections.IEnumerable)planJob.Result["plans"]){
            var p=(Dictionary<string,object>)raw;string id=Convert.ToString(p["id"]),name=Convert.ToString(p["name"]);
            if(id=="e9a42b02-d5df-448d-aa00-03f14749eb61"||name.Equals("Ultimate Performance",StringComparison.OrdinalIgnoreCase)){name="Ultimate Performance plan";ultimate=true;}
            if(Convert.ToBoolean(p["active"]))active=name;
            choices.Items.Add(name,null,(s,e)=>{page="power";tray.Run("power",id,true);Render();});
        }
        if(!ultimate)choices.Items.Add("Ultimate Performance plan",null,(s,e)=>{page="power";tray.Run("power","ultimate",true);Render();});
        bool ready=planJob!=null&&planJob.Result!=null&&planJob.Result.ContainsKey("plans");
        if(!ready&&planJob!=null&&!planJob.Running)active="Refresh power plans";
        GlassButton plans=null;plans=Button(active+"   ▾",0,38,body.ClientSize.Width,42,()=>{if(ready)choices.Show(plans,new Point(0,plans.Height));else tray.Run("plans",null,false);},body);
        plans.AccessibleName="Power plan";plans.Disposed+=(s,e)=>choices.Dispose();plans.Enabled=!tray.Updating;
        Label("QUICK ACTIONS",0,96,360,24,9,true,body);
        int half=(body.ClientSize.Width-12)/2;
        Button("Disk cleanup\nReview & clean",0,130,half,88,()=>Open("scan"),body);
        Button("Connection\nSpeed & latency",half+12,130,half,88,()=>Open("connection"),body);
        Button("Restore point\nCreate checkpoint",0,232,half,88,()=>Open("restore"),body);
        Button("GPU drivers\nCheck versions",half+12,232,half,88,()=>Open("drivers"),body);
        Label(tray.Busy?"An action is running in the background.":"Ready when you need it.",0,343,body.ClientSize.Width,45,10,false,body);
    }
    void Open(string action){page=action;if(!tray.Jobs.ContainsKey(action))tray.Run(action,null,action=="restore");Render();}
    void Back(){Button("‹  Quick actions",0,0,155,36,()=>{page="home";Render();},body);}
    void Settings(){Back();Label("Companion settings",0,62,body.ClientSize.Width,35,17,true,body);Label("Small when idle. Active when you need it.",0,105,body.ClientSize.Width,45,10,false,body);
        var check=new CheckBox{Text="Open on startup",Checked=Program.Setting("Startup","1")=="1",AutoSize=true,BackColor=Color.Transparent,ForeColor=ForeColor};check.Location=new Point(2,170);check.CheckedChanged+=(s,e)=>{try{if(!tray.Preview)Program.Startup(check.Checked);}catch(Exception ex){MessageBox.Show(ex.Message,"Startup setting");}};body.Controls.Add(check);
        Label("Updates install automatically when the app and quick actions are idle.",0,226,body.ClientSize.Width,70,10,false,body);
    }
    void Detail(){Back();string title=new Dictionary<string,string>{{"scan","Disk cleanup"},{"clean","Disk cleanup"},{"connection","Your connection"},{"restore","Restore point"},{"drivers","GPU drivers"},{"updates","App updates"},{"power","Power plan"}}[page];Label(title,0,58,body.ClientSize.Width,38,18,true,body);
        Job job;if(!tray.Jobs.TryGetValue(page,out job)){Label("Ready.",0,112,body.ClientSize.Width,80,11,false,body);return;}
        if(page=="scan"&&job.Result!=null&&job.Result.ContainsKey("items")){
            var selected=new List<CheckBox>();int y=106;
            foreach(var raw in (System.Collections.IEnumerable)job.Result["items"]){var item=(Dictionary<string,object>)raw;var check=new CheckBox{Text=item["name"]+" · "+item["human"],Tag=item["id"],Checked=Convert.ToBoolean(item["default"]),BackColor=Color.Transparent,ForeColor=ForeColor};check.SetBounds(0,y,body.ClientSize.Width-12,32);body.Controls.Add(check);selected.Add(check);y+=35;}
            Button("Clean selected",0,y+10,body.ClientSize.Width-12,44,()=>{var ids=new List<string>();foreach(var c in selected)if(c.Checked)ids.Add(Convert.ToString(c.Tag));if(ids.Count==0)return;page="clean";tray.Run("clean",ids.ToArray(),true);tray.Jobs.Remove("scan");Render();},body,true);return;
        }
        Label(job.Message??"Working…",0,114,body.ClientSize.Width,185,11,false,body);
        if(!job.Running && page!="updates" && page!="power")Button(page=="clean"?"Review cleanup":"Run again",0,310,body.ClientSize.Width,44,()=>{if(page=="clean")page="scan";tray.Run(page,null,page=="restore");Render();},body);
    }
}
sealed class GlassMenuColors:ProfessionalColorTable {
    public override Color MenuBorder{get{return Color.FromArgb(34,49,72);}}
    public override Color MenuItemBorder{get{return Color.FromArgb(55,78,110);}}
    public override Color MenuItemSelected{get{return Color.FromArgb(55,78,110);}}
    public override Color ToolStripDropDownBackground{get{return Color.FromArgb(34,49,72);}}
}
}
