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
        task.RegistrationInfo.Description="Tech Lounge tray companion. Starts shortly after sign-in.";
        task.Principal.UserId=Sid; task.Principal.LogonType=3; task.Principal.RunLevel=0;
        task.Settings.DisallowStartIfOnBatteries=false; task.Settings.StopIfGoingOnBatteries=false;
        task.Settings.ExecutionTimeLimit="PT0S"; task.Settings.MultipleInstances=2;
        dynamic trigger=task.Triggers.Create(9); trigger.UserId=Sid; trigger.Delay="PT30S";
        dynamic action=task.Actions.Create(0); action.Path=Path.Combine(Root,"TechLounge.exe"); action.Arguments="--tray";
        folder.RegisterTaskDefinition(TaskName,task,6,Sid,null,3,null); Save("Startup","1");
    }
    [STAThread] static int Main(string[] args) {
        try {
            PopupDpi.Enable();
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
                    using(var bitmap=popup.Snapshot())bitmap.Save(args[1]);
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

sealed class Job {public bool Running,Failed;public string Message;public Dictionary<string,object> Result;}
sealed class Tray : ApplicationContext {
    public readonly Dictionary<string,Job> Jobs=new Dictionary<string,Job>();
    public bool Preview; public Popup Window; public Color Accent;
    readonly NotifyIcon icon; readonly ContextMenuStrip menu; readonly Control dispatch=new Control();
    readonly EventWaitHandle quit; readonly RegisteredWaitHandle quitWait;
    readonly System.Threading.Timer updateTimer;
    Icon trayImage;
    bool disposed,iconActive,iconLight;Color iconAccent; public bool Updating;public bool UpdateAvailable;
    public Tray(bool preview):this(preview,true){}
    public Tray(bool preview,bool automaticUpdates) {
        Preview=preview; LoadTheme(); dispatch.CreateControl();
        if(preview) {Jobs["plans"]=new Job{Result=new Dictionary<string,object>{{"plans",new object[]{new Dictionary<string,object>{{"id","balanced"},{"name","Balanced"},{"active",true}}}}}};return;}
        icon=new NotifyIcon{Text="Tech Lounge Tweaks"};
        UpdateIcon(false);icon.Visible=true;
        SystemEvents.UserPreferenceChanged+=DesktopAppearanceChanged;
        icon.MouseClick+=(s,e)=>{if(e.Button==MouseButtons.Left)ShowPopup();};
        menu=CreateMenu();
        menu.Items.Add("Quick actions",null,(s,e)=>ShowPopup()).Tag="quick";
        menu.Items.Add("Open app",null,(s,e)=>OpenApp()).Tag="open";
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Exit companion",null,(s,e)=>{if(Busy){ShowPopup();return;}ExitThread();}).Tag="exit";
        icon.ContextMenuStrip=menu;
        quit=new EventWaitHandle(false,EventResetMode.AutoReset,"Local\\TechLoungeQuit-"+Program.Sid);
        quitWait=ThreadPool.RegisterWaitForSingleObject(quit,(s,t)=>Post(()=>ExitThread()),null,-1,true);
        // Check shortly after startup; a timer keeps the idle companion asleep.
        if(automaticUpdates)updateTimer=new System.Threading.Timer(s=>CheckUpdates(false),null,TimeSpan.FromSeconds(30),System.Threading.Timeout.InfiniteTimeSpan);
    }
    public bool Busy {get {foreach(var j in Jobs.Values)if(j.Running)return true;return Updating;}}
    public void LoadTheme(){
        var colors=new Dictionary<string,string>{{"blue","#2f7dff"},{"blurple","#5865f2"},{"purple","#8b5cf6"},{"red","#ff2d6b"},{"green","#16c98a"},{"cyan","#12b6cf"}};
        string name=Program.Setting("Theme","blue"); Accent=ColorTranslator.FromHtml(colors.ContainsKey(name)?colors[name]:colors["blue"]);
    }
    public ContextMenuStrip CreateMenu(){
        var choices=new ThemeMenu{ForeColor=Color.FromArgb(242,244,248),ShowImageMargin=false,Font=Popup.FontFor(10,false)};
        choices.Opening+=(s,e)=>{
            LoadTheme();float scale=PopupDpi.PointerScale();choices.Font=Popup.FontFor(10,false,scale);
            choices.BackColor=Color.FromArgb(24+Accent.R/8,33+Accent.G/8,47+Accent.B/8);
            choices.Renderer=new ThemeMenuRenderer(Accent,scale);
            choices.Padding=new Padding((int)Math.Round(6*scale));
            int width=(int)Math.Round(216*scale);
            foreach(ToolStripItem item in choices.Items)if(!(item is ToolStripSeparator))width=Math.Max(width,TextRenderer.MeasureText(item.Text,choices.Font).Width+(int)Math.Round((item.Tag is string?56:48)*scale));
            foreach(ToolStripItem item in choices.Items){item.AutoSize=false;item.Margin=Padding.Empty;item.Padding=Padding.Empty;item.Size=new Size(width,(int)Math.Round((item is ToolStripSeparator?10:36)*scale));}
            int height=choices.Padding.Vertical;foreach(ToolStripItem item in choices.Items)height+=item.Height;
            choices.AutoSize=false;choices.Size=new Size(width+choices.Padding.Horizontal,height);
        };
        choices.Opened+=(s,e)=>UpdateIcon(true);
        choices.Closed+=(s,e)=>UpdateIcon(Window!=null&&!Window.IsDisposed);
        return choices;
    }
    void DesktopAppearanceChanged(object sender,UserPreferenceChangedEventArgs e){Post(()=>UpdateIcon(Window!=null&&!Window.IsDisposed));}
    public void UpdateIcon(bool active){
        if(icon==null||disposed)return;
        bool light=TrayGlyph.LightTaskbar();
        if(trayImage!=null&&iconActive==active&&iconLight==light&&iconAccent==Accent)return;
        var next=TrayGlyph.Create(Accent,active,light);
        var previous=trayImage;icon.Icon=next;trayImage=next;if(previous!=null)previous.Dispose();
        iconActive=active;iconLight=light;iconAccent=Accent;
    }
    public void Post(Action action){if(!disposed && dispatch.IsHandleCreated)try{dispatch.BeginInvoke(action);}catch(InvalidOperationException){}}
    public void Refresh(){if(Window!=null && !Window.IsDisposed)Window.Render();}
    public void RefreshJob(string action){if(Window!=null&&!Window.IsDisposed)Window.JobChanged(action);}
    public void ShowPopup(){
        var previous=Accent;LoadTheme();UpdateIcon(true);
        if(Window!=null && !Window.IsDisposed){if(previous!=Accent)Window.Render();Window.Reveal();return;}
        Window=new Popup(this);Window.Show();Window.Activate();
        Run("plans",null,false);
    }
    public void OpenApp(bool updates=false){try{Program.Start(Path.Combine(Program.Here,"TechLoungeTweaks.exe"),updates?"--updates":"");if(Window!=null)Window.Close();}catch(Exception ex){Jobs["open"]=new Job{Message=ex.Message};Refresh();}}
    public void Run(string action,object payload,bool elevate) {
        Job existing;if(Jobs.TryGetValue(action,out existing)&&existing.Running)return;
        if(Updating){Jobs[action]=new Job{Message="The updater is busy. Try again shortly."};RefreshJob(action);return;}
        var job=new Job{Running=true,Message="Working…",Result=action=="plans"&&existing!=null?existing.Result:null};Jobs[action]=job;RefreshJob(action);
        Task.Run(async()=>{
            try {
                if(Preview){await Task.Delay(1200);Post(()=>{job.Running=false;job.Message="Preview complete.";RefreshJob(action);});return;}
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
                                if(message.ContainsKey("done")) {Post(()=>{job.Failed=data.ContainsKey("error")||data.ContainsKey("__error__");if(!job.Failed||job.Result==null)job.Result=data;job.Running=false;job.Message=Describe(action,data);if(action=="power"&&data.ContainsKey("plans"))Jobs["plans"]=job;RefreshJob(action);});break;}
                                if(data!=null)Post(()=>ApplyProgress(action,job,data));
                            }
                        }
                    }
                }
            }catch(Exception ex){Post(()=>{job.Running=false;job.Failed=true;job.Message=ex is System.ComponentModel.Win32Exception?"Action cancelled or Windows permission was denied.":ex.Message;RefreshJob(action);});}
        });
    }
    internal void ApplyProgress(string action,Job job,Dictionary<string,object> data){
        bool changed=false;object raw;if(action=="connection"&&data.TryGetValue("res",out raw)&&raw is Dictionary<string,object>){job.Result=(Dictionary<string,object>)raw;changed=true;}
        if(data.TryGetValue("label",out raw)){string label=Convert.ToString(raw);if(job.Message!=label){job.Message=label;changed=true;}}
        if(changed)RefreshJob(action);
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
    public void SetUpdateAvailable(bool available){if(UpdateAvailable==available)return;UpdateAvailable=available;RefreshJob("updates");}
    public void CheckUpdates(bool manual){Post(()=>{
        if(InstallerUpdates.FullAppRunning()){ScheduleUpdate(true);return;}
        if(Busy){if(!Updating){Jobs["updates"]=new Job{Message="Updates will check after the current action finishes."};RefreshJob("updates");ScheduleUpdate(true);}return;}
        Updating=true;Jobs["updates"]=new Job{Running=true,Message="Checking for updates…"};RefreshJob("updates");
        Task.Run(()=>{string status;bool retry;try{status=InstallerUpdates.Run(this,manual,out retry);}catch(Exception ex){retry=false;status="Update check unavailable. Will retry later. "+ex.Message;}
            Post(()=>{Updating=false;Jobs["updates"].Running=false;Jobs["updates"].Message=status;RefreshJob("updates");ScheduleUpdate(retry);if(!InstallerUpdates.FullAppRunning())Run("update-tools",null,false);});});
    });}
    void ScheduleUpdate(bool retry){if(updateTimer!=null)updateTimer.Change(retry?TimeSpan.FromMinutes(1):TimeSpan.FromMinutes(15),System.Threading.Timeout.InfiniteTimeSpan);}
    protected override void Dispose(bool disposing){disposed=true;if(disposing){if(updateTimer!=null)updateTimer.Dispose();if(quitWait!=null)quitWait.Unregister(null);if(quit!=null)quit.Dispose();if(icon!=null){SystemEvents.UserPreferenceChanged-=DesktopAppearanceChanged;icon.Visible=false;icon.Dispose();}if(menu!=null)menu.Dispose();if(trayImage!=null)trayImage.Dispose();if(Window!=null)Window.Dispose();dispatch.Dispose();}base.Dispose(disposing);}
}

sealed class GlassButton:Button {
    public Color Tint; public bool Primary;public string Symbol;
    protected override void WndProc(ref Message message){TrayGeometry.DiscardCopiedPixels(ref message,true);base.WndProc(ref message);}
    public GlassButton(){FlatStyle=FlatStyle.Flat;FlatAppearance.BorderSize=0;ForeColor=Color.FromArgb(232,238,248);Font=Popup.FontFor(10,true);Cursor=PopupDpi.HandCursor();SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint,true);}
    protected override void OnPaint(PaintEventArgs e){
        // ButtonBase is opaque and can skip OnPaintBackground. Paint the complete
        // backing surface here before blending the translucent rounded fill.
        var popup=FindForm() as Popup;
        if(popup!=null){
            var offset=popup.PointToClient(PointToScreen(Point.Empty));
            popup.PaintBackdrop(e.Graphics,new Rectangle(-offset.X,-offset.Y,popup.ClientSize.Width,popup.ClientSize.Height));
        }else using(var fill=new SolidBrush(BackColor))e.Graphics.FillRectangle(fill,ClientRectangle);
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        var box=new Rectangle(0,0,Width-1,Height-1);
        int radius=popup==null?10:popup.Pixels(10);
        using(var shape=Popup.Round(box,radius)){
            using(var fill=new SolidBrush(Primary?Color.FromArgb(210,Tint):Color.FromArgb(Focused||ClientRectangle.Contains(PointToClient(Cursor.Position))?52:25,180,200,235)))e.Graphics.FillPath(fill,shape);
            using(var rim=new Pen(Color.FromArgb(18,255,255,255)))e.Graphics.DrawPath(rim,shape);
        }
        if(Text=="⚙"&&popup!=null){
            var teeth=new PointF[32];float cx=Width/2f,cy=Height/2f;
            for(int i=0;i<8;i++)for(int j=0;j<4;j++){
                double angle=(i+(j==0?-.5:j==1?-.23:j==2?.23:.5))*Math.PI/4-Math.PI/2;
                float gearRadius=popup.Pixels(j==1||j==2?9:7);
                teeth[i*4+j]=new PointF(cx+(float)Math.Cos(angle)*gearRadius,cy+(float)Math.Sin(angle)*gearRadius);
            }
            using(var pen=new Pen(ForeColor,Math.Max(1,popup.Pixels(1)))){
                pen.LineJoin=LineJoin.Round;e.Graphics.DrawPolygon(pen,teeth);
                int hole=popup.Pixels(3);e.Graphics.DrawEllipse(pen,cx-hole,cy-hole,hole*2,hole*2);
            }
            if(Focused&&ShowFocusCues)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(box,-5,-5),ForeColor,BackColor);
            return;
        }
        var flags=TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.WordBreak|TextFormatFlags.NoPrefix|TextFormatFlags.PreserveGraphicsClipping|TextFormatFlags.PreserveGraphicsTranslateTransform;
        if(Symbol!=null&&popup!=null){
            int inset=popup.Pixels(12),size=popup.Pixels(18);
            TraySymbols.Draw(e.Graphics,Symbol,new Rectangle(inset,(Height-size)/2,size,size),Tint);
            TextRenderer.DrawText(e.Graphics,Text,Font,new Rectangle(popup.Pixels(42),0,Width-popup.Pixels(70),Height),ForeColor,(flags&~TextFormatFlags.HorizontalCenter)|TextFormatFlags.Left|TextFormatFlags.SingleLine|TextFormatFlags.EndEllipsis);
            TextRenderer.DrawText(e.Graphics,"›",Font,new Rectangle(Width-popup.Pixels(28),0,popup.Pixels(20),Height),Color.FromArgb(176,191,212),flags);return;
        }
        var lines=Text.Split('\n');
        if(lines.Length==2&&popup!=null){
            TextRenderer.DrawText(e.Graphics,lines[0],Font,new Rectangle(0,Height/2-popup.Pixels(21),Width,popup.Pixels(24)),Enabled?ForeColor:Color.Gray,flags);
            TextRenderer.DrawText(e.Graphics,lines[1],popup.FontAt(9,false),new Rectangle(0,Height/2+popup.Pixels(2),Width,popup.Pixels(22)),Enabled?Color.FromArgb(176,191,212):Color.Gray,flags);
        }else TextRenderer.DrawText(e.Graphics,Text,Font,box,Enabled?ForeColor:Color.Gray,flags);
        if(Focused&&ShowFocusCues)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(box,-5,-5),ForeColor,BackColor);
    }
}
sealed class Popup:Form {
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
    [System.Runtime.InteropServices.DllImport("dwmapi.dll")] static extern int DwmFlush();
    static readonly Dictionary<string,Font> fonts=new Dictionary<string,Font>();
    internal static Font FontFor(int size,bool bold,float scale=0){if(scale==0)scale=PopupDpi.PointerScale();string key=size+":"+bold+":"+scale;Font font;if(!fonts.TryGetValue(key,out font)){float points=size==9?9.5f:size==10?10.5f:size;string family=bold?"Segoe UI Variable Text Semibold":"Segoe UI Variable Text";font=new Font(family,points*4f/3f*scale,FontStyle.Regular,GraphicsUnit.Pixel);if(!font.Name.StartsWith("Segoe UI Variable",StringComparison.Ordinal)){font.Dispose();font=new Font("Segoe UI",points*4f/3f*scale,bold?FontStyle.Bold:FontStyle.Regular,GraphicsUnit.Pixel);}fonts[key]=font;}return font;}
    readonly Tray tray; readonly TrayBodyPanel body=new TrayBodyPanel();string page="home";
    readonly PopupMotion motion;
    readonly GlassButton secondaryFooter,openFooter,settingsButton;bool splitFooter;
    readonly TrayPageMotion pageMotion;string renderedPage;
    Label detailMessage,homeStatus;
    readonly Dictionary<string,TrayMetricCard> connectionCards=new Dictionary<string,TrayMetricCard>();GlassButton connectionRetry;
    float uiScale;
    object cleanupResult;readonly HashSet<string> cleanupSelected=new HashSet<string>();
    internal Font FontAt(int size,bool bold){return FontFor(size,bold,uiScale);}
    internal int Pixels(int value){return (int)Math.Round(value*uiScale);}
    int LayoutWidth {get{return (int)Math.Round(ClientSize.Width/uiScale);}}
    int LayoutHeight {get{return (int)Math.Round(ClientSize.Height/uiScale);}}
    internal int Logical(int pixels){return (int)Math.Ceiling(pixels/uiScale);}
    int PopupHeight {get{
        Job job;
        if(page=="scan"&&tray.Jobs.TryGetValue("scan",out job)&&job.Result!=null&&job.Result.ContainsKey("items")){
            int count=0;foreach(var item in (System.Collections.IEnumerable)job.Result["items"])count++;
            return Math.Max(430,182+count*32);
        }
        if(page=="drivers"&&tray.Jobs.TryGetValue("drivers",out job)&&job.Result!=null&&job.Result.ContainsKey("gpus")){
            int height=44;foreach(var raw in (System.Collections.IEnumerable)job.Result["gpus"]){var gpu=(Dictionary<string,object>)raw;height+=TrayGpuCard.HeightFor(gpu,this,LayoutWidth-40)+12;if(DriverLinks.UpdateUrl(gpu)!=null)height+=44;}
            return Math.Max(380,height+128);
        }
        return page=="connection"?450:page=="settings"?380:430;
    }}
    int BodyHeight {get{return (int)Math.Floor(body.ClientSize.Height/uiScale);}}
    int BodyWidth {get{return (int)Math.Round(body.ClientSize.Width/uiScale);}}
    protected override void WndProc(ref Message message){
        if(message.Msg==0x02E0&&pageMotion!=null){
            motion.Settle();pageMotion.Pause();float next=(message.WParam.ToInt64()&0xffff)/96f;
            if(next>0&&Math.Abs(next-uiScale)>.001f){
                float ratio=next/uiScale;uiScale=next;
                foreach(Control c in Controls)if(c!=body){c.Bounds=new Rectangle((int)Math.Round(c.Left*ratio),(int)Math.Round(c.Top*ratio),(int)Math.Round(c.Width*ratio),(int)Math.Round(c.Height*ratio));if(c is Label)c.Font=FontAt(16,true);}
                var work=Screen.FromHandle(Handle).WorkingArea;
                ClientSize=new Size(Math.Min(Pixels(380),work.Width-Pixels(28)),Math.Min(Pixels(PopupHeight),work.Height-Pixels(28)));
                Location=new Point(work.Right-Width-Pixels(14),work.Bottom-Height-Pixels(14));
                openFooter.Font=FontAt(10,true);settingsButton.Font=FontAt(10,true);
                body.Top=Pixels(64);body.Left=Pixels(20);pageMotion.SetBaseLeft(Pixels(20));Render();
            }
            message.Result=IntPtr.Zero;return;
        }
        TrayGeometry.DiscardCopiedPixels(ref message,false);base.WndProc(ref message);
    }
    public Popup(Tray owner){
        tray=owner;Text="Tech Lounge quick actions";FormBorderStyle=FormBorderStyle.None;ShowInTaskbar=false;TopMost=true;StartPosition=FormStartPosition.Manual;
        uiScale=PopupDpi.PointerScale();AutoScaleMode=AutoScaleMode.None;DoubleBuffered=true;SetStyle(ControlStyles.ResizeRedraw|ControlStyles.AllPaintingInWmPaint,true);BackColor=Color.FromArgb(24,35,53);ForeColor=Color.FromArgb(242,244,248);Font=FontAt(10,false);KeyPreview=true;
        KeyDown+=(s,e)=>{if(e.KeyCode==Keys.Escape)Close();};
        var area=Screen.FromPoint(Cursor.Position).WorkingArea;ClientSize=new Size(Math.Min(Pixels(380),area.Width-Pixels(28)),Math.Min(Pixels(PopupHeight),area.Height-Pixels(28)));Location=new Point(area.Right-Width-Pixels(14),area.Bottom-Height-Pixels(14));
        body.SetBounds(Pixels(20),Pixels(64),ClientSize.Width-Pixels(40),ClientSize.Height-Pixels(128));body.BackColor=Color.Transparent;body.AutoScroll=false;Controls.Add(body);
        // Keep native chrome handles alive across page changes. Only the content changes.
        Label("Tech Lounge",20,16,LayoutWidth-88,28,16,true,this);
        settingsButton=Button("⚙",LayoutWidth-56,14,36,36,()=>{page="settings";Render();},this);settingsButton.AccessibleName="Companion settings";
        secondaryFooter=Button("",20,LayoutHeight-52,180,36,()=>{if(page=="scan")CleanSelected();else if(page=="connection")tray.Run("connection",null,false);else if(page=="home"&&tray.UpdateAvailable)tray.OpenApp(true);},this);secondaryFooter.Visible=false;
        openFooter=Button("Open app",20,LayoutHeight-52,LayoutWidth-40,36,()=>tray.OpenApp(),this,true);
        motion=new PopupMotion(this,Pixels(12),PopupMotion.Enabled());
        pageMotion=new TrayPageMotion(this,body,Pixels(20),LayoutPageChrome,()=>motion.Running);
        Shown+=(s,e)=>{Update();motion.Show();SetForegroundWindow(Handle);};
        Activated+=(s,e)=>motion.Reopen();
        Deactivate+=(s,e)=>QueueDismiss();FormClosed+=(s,e)=>{tray.Window=null;tray.UpdateIcon(false);};Render();
    }
    internal Bitmap Snapshot(){
        motion.Settle();pageMotion.Settle();Opacity=1;Invalidate(true);Update();Application.DoEvents();DwmFlush();
        using(var raw=new Bitmap(Width,Height,System.Drawing.Imaging.PixelFormat.Format24bppRgb)){
            using(var capture=Graphics.FromImage(raw))capture.CopyFromScreen(Location,Point.Empty,Size);
            var bitmap=new Bitmap(Width,Height,System.Drawing.Imaging.PixelFormat.Format32bppArgb);
            using(var graphics=Graphics.FromImage(bitmap)){graphics.Clear(Color.Transparent);if(Region!=null)graphics.SetClip(Region,CombineMode.Replace);graphics.DrawImageUnscaled(raw,0,0);}
            return bitmap;
        }
    }
    internal void Reveal(){motion.Reopen();pageMotion.Resume();Activate();}
    void QueueDismiss(){if(!IsDisposed&&IsHandleCreated)BeginInvoke((Action)(()=>{
        // Focus has not necessarily moved yet inside the Deactivate event.
        if(IsDisposed||ContainsFocus)return;
        foreach(Control c in body.Controls)if(c.ContextMenuStrip!=null&&c.ContextMenuStrip.Visible)return;
        Close();
    }));}
    public static GraphicsPath Round(Rectangle r,int radius){var p=new GraphicsPath();int d=radius*2;p.AddArc(r.X,r.Y,d,d,180,90);p.AddArc(r.Right-d,r.Y,d,d,270,90);p.AddArc(r.Right-d,r.Bottom-d,d,d,0,90);p.AddArc(r.X,r.Bottom-d,d,d,90,90);p.CloseFigure();return p;}
    protected override void OnPaint(PaintEventArgs e){
        base.OnPaint(e);e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        PaintBackdrop(e.Graphics,ClientRectangle);
    }
    internal void PaintBackdrop(Graphics graphics,Rectangle bounds){
        using(var b=new SolidBrush(Color.FromArgb(25,32,43)))graphics.FillRectangle(b,bounds);
    }
    protected override void OnResize(EventArgs e){base.OnResize(e);if(Width>0&&Height>0)using(var p=Round(ClientRectangle,Math.Max(1,Pixels(12)))){var old=Region;Region=new Region(p);if(old!=null)old.Dispose();}}
    Label Label(string text,int x,int y,int width,int height,int size,bool bold,Control parent){var l=new Label{Text=text,BackColor=Color.Transparent,ForeColor=ForeColor,Font=FontAt(size,bold),UseCompatibleTextRendering=false};l.SetBounds(Pixels(x),Pixels(y),Pixels(width),Pixels(height));parent.Controls.Add(l);return l;}
    GlassButton Button(string text,int x,int y,int w,int h,Action click,Control parent,bool primary=false){var b=new GlassButton{Text=text,Tint=tray.Accent,Primary=primary,BackColor=BackColor,Font=FontAt(10,true)};b.SetBounds(Pixels(x),Pixels(y),Pixels(w),Pixels(h));b.Click+=(s,e)=>click();parent.Controls.Add(b);return b;}
    void LayoutPageChrome(){
        int margin=Pixels(20),gap=Pixels(12),top=ClientSize.Height-Pixels(52);
        body.Width=Math.Max(1,ClientSize.Width-margin*2);
        body.Height=Math.Max(1,top-Pixels(12)-body.Top);
        if(openFooter!=null&&!openFooter.IsDisposed){
            if(secondaryFooter!=null&&!secondaryFooter.IsDisposed&&splitFooter){
                int width=(ClientSize.Width-margin*2-gap)/2;
                secondaryFooter.SetBounds(margin,top+(Pixels(36)-secondaryFooter.Height)/2,width,secondaryFooter.Height);
                openFooter.SetBounds(margin+width+gap,top,ClientSize.Width-margin*2-gap-width,Pixels(36));
            }else openFooter.SetBounds(margin,top,ClientSize.Width-margin*2,Pixels(36));
        }
        settingsButton.Left=ClientSize.Width-Pixels(56);
        foreach(Control chrome in Controls)if(chrome is Label)chrome.Width=Math.Max(1,ClientSize.Width-Pixels(88));
        // Clear the previous footer backing when the animated window changes height.
        Invalidate();
        if(!motion.Running)motion.Reanchor();
    }
    void UpdateCleanupSelection(){
        if(page!="scan"||secondaryFooter==null||secondaryFooter.IsDisposed)return;
        int selected=0;foreach(Control c in body.Controls)if(c is CheckBox&&((CheckBox)c).Checked)selected++;
        secondaryFooter.Text="Clean selected"+(selected>0?" ("+selected+")":"");
        Job scan;secondaryFooter.Enabled=selected>0&&tray.Jobs.TryGetValue("scan",out scan)&&!scan.Running&&scan.Result!=null;
    }
    void CleanSelected(){
        var ids=new List<string>();foreach(Control c in body.Controls)if(c is CheckBox&&((CheckBox)c).Checked)ids.Add(Convert.ToString(c.Tag));
        if(ids.Count==0)return;
        page="clean";tray.Run("clean",ids.ToArray(),true);tray.Jobs.Remove("scan");Render();
    }
    public void Render(){
        bool continuing=pageMotion.Running;int offset=pageMotion.Offset;var previous=Bounds;
        bool animate=Visible&&PopupMotion.Enabled()&&(renderedPage!=page||continuing);
        pageMotion.Pause();
        using(var redraw=new TrayRedrawBatch(this,body)){
        SuspendLayout();try{
        if(animate)motion.Settle();
        var work=Screen.FromPoint(new Point(Left+Width/2,Top+Height/2)).WorkingArea;
        int height=Math.Min(Pixels(PopupHeight),work.Height-Pixels(28));
        if(ClientSize.Height!=height){if(Visible)motion.Settle();int bottom=Bottom;ClientSize=new Size(ClientSize.Width,height);Top=Math.Max(work.Top+Pixels(14),bottom-Height);if(Visible)motion.Reanchor();}
        body.Height=ClientSize.Height-Pixels(128);
        bool hadCleanup=false;foreach(Control c in body.Controls)if(c is CheckBox&&c.Tag is string){if(!hadCleanup){cleanupSelected.Clear();hadCleanup=true;}if(((CheckBox)c).Checked)cleanupSelected.Add((string)c.Tag);}
        foreach(Control c in Children(body))c.Dispose();body.Controls.Clear();detailMessage=null;homeStatus=null;connectionCards.Clear();connectionRetry=null;
        splitFooter=page=="scan"||page=="connection"||(page=="home"&&tray.UpdateAvailable);
        settingsButton.Tint=tray.Accent;secondaryFooter.Tint=tray.Accent;openFooter.Tint=tray.Accent;
        secondaryFooter.Visible=splitFooter;secondaryFooter.Enabled=false;
        secondaryFooter.Text=page=="scan"?"Clean selected":page=="connection"?"Test again":splitFooter?"● Update available":"";
        secondaryFooter.Primary=page=="scan";secondaryFooter.Height=Pixels(page=="home"?28:36);
        secondaryFooter.Font=FontAt(page=="home"?9:10,page!="home");
        secondaryFooter.AccessibleName=page=="scan"?"Clean selected":page=="connection"?"Test again":"Update available. Open full app update details";
        if(page=="home"&&splitFooter)secondaryFooter.Enabled=true;
        openFooter.Primary=page!="scan";
        LayoutPageChrome();
        if(page=="home")Home();else if(page=="settings")Settings();else Detail();
        var destination=Bounds;
        pageMotion.Start(previous.Size==destination.Size?previous:destination,destination,continuing?offset:Pixels(page=="home"?-14:14),animate);
        renderedPage=page;Invalidate();
        }finally{ResumeLayout();}
        }
    }
    static List<Control> Children(Control parent){var result=new List<Control>();foreach(Control c in parent.Controls)result.Add(c);return result;}
    void Home(){
        AddSymbol("power",0,0,22,tray.Accent);Label("Power plan",28,0,BodyWidth-28,22,10,true,body);
        var choices=tray.CreateMenu();
        string active="Loading plans…";bool ultimate=false;Job planJob;
        if(tray.Jobs.TryGetValue("plans",out planJob)&&planJob.Result!=null&&planJob.Result.ContainsKey("plans"))foreach(var raw in (System.Collections.IEnumerable)planJob.Result["plans"]){
            var p=(Dictionary<string,object>)raw;string id=Convert.ToString(p["id"]),name=Convert.ToString(p["name"]);
            if(id=="e9a42b02-d5df-448d-aa00-03f14749eb61"||name.Equals("Ultimate Performance",StringComparison.OrdinalIgnoreCase)){name="Ultimate Performance plan";ultimate=true;}
            if(Convert.ToBoolean(p["active"]))active=name;
            var option=(ToolStripMenuItem)choices.Items.Add(name,null,(s,e)=>tray.Run("power",id,true));option.Checked=Convert.ToBoolean(p["active"]);
        }
        if(!ultimate)choices.Items.Add("Ultimate Performance plan",null,(s,e)=>tray.Run("power","ultimate",true));
        bool ready=planJob!=null&&planJob.Result!=null&&planJob.Result.ContainsKey("plans");
        if(!ready&&planJob!=null&&!planJob.Running)active="Refresh power plans";
        long dismissedFromSelector=0;
        GlassButton plans=null;plans=Button(active+"   ▾",0,26,BodyWidth,36,()=>{
            bool sameClick=dismissedFromSelector!=0&&(Stopwatch.GetTimestamp()-dismissedFromSelector)*1000.0/Stopwatch.Frequency<500;
            dismissedFromSelector=0;
            if(sameClick)return;
            if(choices.Visible){choices.Close();return;}
            if(ready){motion.Settle();choices.Show(plans,new Point(0,plans.Height));}else tray.Run("plans",null,false);
        },body);
        choices.Closing+=(s,e)=>{if(e.CloseReason==ToolStripDropDownCloseReason.AppClicked&&plans.ClientRectangle.Contains(plans.PointToClient(Cursor.Position)))dismissedFromSelector=Stopwatch.GetTimestamp();};
        plans.AccessibleName="Power plan";plans.ContextMenuStrip=choices;choices.Closed+=(s,e)=>QueueDismiss();plans.Disposed+=(s,e)=>choices.Dispose();Job powerJob;bool switching=tray.Jobs.TryGetValue("power",out powerJob)&&powerJob.Running;plans.Enabled=!tray.Updating&&!switching;
        Button("Disk cleanup",0,78,BodyWidth,36,()=>Open("scan"),body).Symbol="clean";
        Button("Connection",0,122,BodyWidth,36,()=>Open("connection"),body).Symbol="network";
        Button("Restore point",0,166,BodyWidth,36,()=>Open("restore"),body).Symbol="restore";
        var gpuButton=Button("GPU drivers",0,210,BodyWidth,36,()=>Open("drivers"),body);gpuButton.Symbol="gpu";
        Job driverJob;if(tray.Jobs.TryGetValue("drivers",out driverJob)&&!driverJob.Running&&driverJob.Result!=null&&driverJob.Result.ContainsKey("gpus")){
            bool outdated=false,verified=true;int count=0;
            foreach(var raw in (System.Collections.IEnumerable)driverJob.Result["gpus"]){var gpu=(Dictionary<string,object>)raw;string status=Convert.ToString(gpu["status"]);outdated|=status=="update";verified&=status=="current"||status=="ahead";count++;}
            if(outdated){gpuButton.Text="GPU drivers · Out of date";gpuButton.Tint=Color.FromArgb(255,190,61);}
            else if(verified&&count>0){gpuButton.Text="GPU drivers · Up to date";gpuButton.Tint=Color.FromArgb(61,220,151);}
        }
        homeStatus=Label("",0,252,BodyWidth,28,9,false,body);homeStatus.Visible=false;UpdateHomeStatus();
    }
    void UpdateHomeStatus(){
        if(homeStatus==null||homeStatus.IsDisposed)return;
        Job powerJob;tray.Jobs.TryGetValue("power",out powerJob);
        bool failed=powerJob!=null&&!powerJob.Running&&(powerJob.Result==null||powerJob.Result.ContainsKey("error")||powerJob.Result.ContainsKey("__error__"));
        homeStatus.Text=failed?powerJob.Message:tray.Busy?"An action is running in the background.":"";
        homeStatus.Visible=homeStatus.Text!="";if(homeStatus.Visible)FitMessage(homeStatus);body.PerformLayout();
        homeStatus.ForeColor=failed?Color.FromArgb(255,185,178):Color.FromArgb(176,191,212);
    }
    internal void JobChanged(string action){
        if(page=="home"){
            if(action=="plans"||action=="power"||action=="updates"||action=="drivers")Render();else UpdateHomeStatus();
            return;
        }
        if(page!=action)return;
        if(page=="connection"&&connectionCards.Count==4){UpdateConnection();return;}
        Job job;if(tray.Jobs.TryGetValue(action,out job)&&job.Running&&detailMessage!=null&&!detailMessage.IsDisposed){
            detailMessage.Text=job.Message??"Working…";FitMessage(detailMessage);return;
        }
        Render();
    }
    void FitMessage(Label message){message.Height=Math.Max(Pixels(28),TextRenderer.MeasureText(message.Text,message.Font,new Size(message.Width,int.MaxValue),TextFormatFlags.WordBreak|TextFormatFlags.NoPrefix).Height+Pixels(12));}
    void Open(string action){page=action;if(!tray.Jobs.ContainsKey(action)){tray.Run(action,null,action=="restore");return;}Render();}
    void Back(){Button("‹",0,0,28,30,()=>{page="home";Render();},body).AccessibleName="Back to Quick actions";}
    void Settings(){Back();PageTitle("Companion settings","startup",0);
        var check=new TrayCheckBox{Tint=tray.Accent,Font=FontAt(10,false),Text="Open on startup",Checked=Program.Setting("Startup","1")=="1",AutoSize=false,BackColor=Color.Transparent,ForeColor=ForeColor};check.SetBounds(0,Pixels(54),Pixels(BodyWidth-14),Pixels(44));check.CheckedChanged+=(s,e)=>{try{if(!tray.Preview)Program.Startup(check.Checked);}catch(Exception ex){MessageBox.Show(ex.Message,"Startup setting");}};body.Controls.Add(check);
        AddSymbol("restore",0,120,28,tray.Accent);Label("Automatic updates",40,114,BodyWidth-40,30,12,true,body);Label("The app and supported tools update quietly. The app restarts when jobs and tools are idle.",40,150,BodyWidth-40,66,10,false,body);
    }
    void AddSymbol(string symbol,int x,int y,int size,Color tint){var badge=new TraySymbolBadge(symbol,tint);badge.SetBounds(Pixels(x),Pixels(y),Pixels(size),Pixels(size));body.Controls.Add(badge);}
    void PageTitle(string title,string symbol,int y){AddSymbol(symbol,40,y+2,24,tray.Accent);Label(title,76,y,BodyWidth-112,32,15,true,body);}
    void ConnectionCard(Dictionary<string,object> data,string key,string title,string unit,string icon,int x,int y,int width){
        object raw;data.TryGetValue(key,out raw);var card=new TrayMetricCard(title,raw,unit,icon,tray.Accent);card.SetBounds(Pixels(x),Pixels(y),Pixels(width),Pixels(96));body.Controls.Add(card);connectionCards[key]=card;
    }
    void UpdateConnection(){
        Job job;if(!tray.Jobs.TryGetValue("connection",out job))return;
        foreach(var pair in connectionCards){object value=null;bool found=job.Result!=null&&job.Result.TryGetValue(pair.Key,out value);string unit=pair.Key=="idle_ms"?"ms · Idle":pair.Key=="grade"?"":"Mbps";if(pair.Key=="download_mbps"&&job.Result!=null&&job.Result.ContainsKey("download_server"))unit+=" · "+Convert.ToString(job.Result["download_server"]).Replace("Clouvider ","");string phase=pair.Key=="download_mbps"?"download":pair.Key=="upload_mbps"?"upload":pair.Key=="idle_ms"?"idle":"grade";bool live=false;object fields;if(job.Running&&job.Result!=null&&job.Result.TryGetValue("live_fields",out fields)&&fields is System.Collections.IEnumerable)foreach(object field in (System.Collections.IEnumerable)fields)if(Convert.ToString(field)==pair.Key)live=true;pair.Value.UpdateValue(value,unit,job.Running&&!found,(job.Message??"").ToLowerInvariant().Contains(phase),live);}
        string status="Bufferbloat measures lag under load. A+ is best.";
        if(job.Running)status=job.Message??"Testing connection…";
        else if(job.Failed||job.Result==null)status=job.Message;
        else if(job.Result.ContainsKey("error"))status=Convert.ToString(job.Result["error"]);
        else if(job.Result.ContainsKey("download_error")&&job.Result.ContainsKey("upload_error"))status="Speed test unavailable. Please test again.";
        else if(job.Result.ContainsKey("download_error"))status="Download unavailable. Please test again.";
        else if(job.Result.ContainsKey("upload_error"))status="Upload unavailable. Please test again.";
        if(detailMessage!=null)detailMessage.Text=status;
        if(connectionRetry!=null){connectionRetry.Enabled=!job.Running;connectionRetry.Text=job.Running?"Testing…":"Test again";}
    }
    void OpenDriverLink(string url,string vendor){
        if(!DriverLinks.IsOfficial(url,vendor))return;
        if(tray.Preview)return;
        try{Process.Start(new ProcessStartInfo(url){UseShellExecute=true});}
        catch(Exception ex){MessageBox.Show(this,"Could not open the driver page. "+ex.Message,"GPU drivers",MessageBoxButtons.OK,MessageBoxIcon.Information);}
    }
    void Detail(){Back();string title=new Dictionary<string,string>{{"scan","Disk cleanup"},{"clean","Disk cleanup"},{"connection","Your connection"},{"restore","Restore point"},{"drivers","GPU drivers"},{"power","Power plan"}}[page];PageTitle(title,page=="connection"?"network":page=="drivers"?"gpu":page=="restore"?"restore":page=="power"?"power":"clean",0);
        Job job;if(!tray.Jobs.TryGetValue(page,out job)){Label("Ready.",0,44,BodyWidth-14,36,10,false,body);return;}
        if(page=="scan"&&job.Result!=null&&job.Result.ContainsKey("items")){
            if(!object.ReferenceEquals(cleanupResult,job.Result)){cleanupResult=job.Result;cleanupSelected.Clear();foreach(var raw in (System.Collections.IEnumerable)job.Result["items"]){var item=(Dictionary<string,object>)raw;if(Convert.ToBoolean(item["default"]))cleanupSelected.Add(Convert.ToString(item["id"]));}}
            var rows=new List<CheckBox>();
            foreach(var raw in (System.Collections.IEnumerable)job.Result["items"]){var item=(Dictionary<string,object>)raw;var check=new TrayCheckBox{Tint=tray.Accent,Font=FontAt(10,false),Text=item["name"]+" · "+item["human"],Tag=item["id"],Checked=cleanupSelected.Contains(Convert.ToString(item["id"])),BackColor=Color.Transparent,ForeColor=ForeColor};check.SetBounds(0,Pixels(44+rows.Count*32),Pixels(BodyWidth),Pixels(28));check.CheckedChanged+=(s,e)=>UpdateCleanupSelection();body.Controls.Add(check);rows.Add(check);}
            UpdateCleanupSelection();return;
        }
        if(page=="drivers"){
            var refresh=Button("↻",BodyWidth-28,0,28,30,()=>tray.Run("drivers",null,false),body);refresh.AccessibleName="Check again";refresh.Enabled=!job.Running;
            if(job.Result!=null&&job.Result.ContainsKey("gpus")){
                int y=44;
                foreach(var raw in (System.Collections.IEnumerable)job.Result["gpus"]){
                    var gpu=(Dictionary<string,object>)raw;var card=new TrayGpuCard(gpu);int height=TrayGpuCard.HeightFor(gpu,this,BodyWidth);card.SetBounds(0,Pixels(y),Pixels(BodyWidth),Pixels(height));body.Controls.Add(card);y+=height;
                    string url=DriverLinks.UpdateUrl(gpu),vendor=gpu.ContainsKey("vendor")?Convert.ToString(gpu["vendor"]):"";
                    if(url!=null){y+=8;Button(gpu.ContainsKey("url")&&url==Convert.ToString(gpu["url"])?"Download update":"Open "+vendor+" drivers",0,y,BodyWidth,36,()=>OpenDriverLink(url,vendor),body,true);y+=36;}
                    y+=12;
                }
                if(y==44)Label("No supported GPU detected.",0,44,BodyWidth,36,10,false,body);return;
            }
        }
        if(page=="connection"){
            var data=job.Result??new Dictionary<string,object>();int half=(BodyWidth-12)/2;
            ConnectionCard(data,"download_mbps","Download","Mbps","download",0,44,half);
            ConnectionCard(data,"upload_mbps","Upload","Mbps","upload",half+12,44,half);
            ConnectionCard(data,"idle_ms","Latency","ms","latency",0,152,half);
            ConnectionCard(data,"grade","Bufferbloat","","grade",half+12,152,half);
            detailMessage=Label("",0,260,BodyWidth,32,9,false,body);detailMessage.ForeColor=Color.FromArgb(176,191,212);
            connectionRetry=secondaryFooter;UpdateConnection();return;
        }
        bool failed=job.Failed||(job.Result!=null&&(job.Result.ContainsKey("error")||(job.Result.ContainsKey("ok")&&!Convert.ToBoolean(job.Result["ok"]))));
        if(job.Running){var loading=new TrayActivityIndicator(tray.Accent);loading.SetBounds(0,Pixels(48),Pixels(22),Pixels(22));body.Controls.Add(loading);}
        if(!job.Running)AddSymbol(failed?"notice":"check",0,44,36,failed?Color.FromArgb(255,190,61):Color.FromArgb(61,220,151));
        var message=Label(job.Message??"Working…",job.Running?32:0,job.Running?44:92,BodyWidth-(job.Running?46:14),28,10,true,body);detailMessage=message;FitMessage(message);
        if(!job.Running && page!="power")Button(page=="clean"?"Review cleanup":"Run again",0,(int)Math.Ceiling(message.Bottom/uiScale)+12,BodyWidth-14,36,()=>{if(page=="clean")page="scan";tray.Run(page,null,page=="restore");Render();},body);
    }
}
}
