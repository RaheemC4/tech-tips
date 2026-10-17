using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

namespace TechLoungeSetup {
static class Program {
    public static string Root;
    [STAThread] static int Main(string[] args) {
        bool silent=Array.Exists(args,a=>a.Equals("/S",StringComparison.OrdinalIgnoreCase));
        bool update=Array.Exists(args,a=>a.Equals("/UPDATE",StringComparison.OrdinalIgnoreCase));
        try {
            Root=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","TechLoungeTweaks");
            using(var key=Registry.CurrentUser.OpenSubKey(@"Software\TechLoungeTweaks"))if(key!=null)Root=Convert.ToString(key.GetValue("InstallRoot",Root));
            for(int i=0;i<args.Length;i++)if(args[i].StartsWith("/D=",StringComparison.OrdinalIgnoreCase)){Root=String.Join(" ",args,i,args.Length-i).Substring(3).Trim('"');break;}
            Root=Path.GetFullPath(Root).TrimEnd(Path.DirectorySeparatorChar);
            if(Root.Length<4 || Root.IndexOf('"')>=0)throw new IOException("Choose a valid application installation folder.");
            bool owner;
            using(var gate=new Mutex(true,@"Local\TechLoungeSetup-"+System.Security.Principal.WindowsIdentity.GetCurrent().User.Value,out owner)){
                if(!owner)return 1618;
                try {
                    using(var run=new Installation(Root,update)){
                        if(silent)return run.Run();
                        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
                        using(var form=new SetupWindow(run))Application.Run(form);
                        return run.ExitCode;
                    }
                }finally{gate.ReleaseMutex();}
            }
        } catch(Exception ex){if(!silent)MessageBox.Show(ex.Message,"Tech Lounge setup",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;}
    }
}

sealed class Installation:IDisposable {
    public readonly string Root;
    readonly bool update;
    readonly string cache=Path.Combine(Path.GetTempPath(),"TechLoungeSetup-"+Guid.NewGuid().ToString("N"));
    volatile bool cancel;
    public volatile int Percent,Stage;
    public string Error,Warning;
    public int ExitCode=0;
    public bool CancelRequested {get{return cancel;}}
    public Installation(string root,bool isUpdate){Root=root;update=isUpdate;}
    public void Cancel(){cancel=true;}
    public int Run(){
        try {
            Directory.CreateDirectory(cache);
            string engine=Path.Combine(cache,"engine.exe"),status=Path.Combine(cache,"status.txt");
            using(var input=new FileStream(Assembly.GetExecutingAssembly().Location,FileMode.Open,FileAccess.Read,FileShare.Read))
            using(var output=new FileStream(engine,FileMode.CreateNew,FileAccess.Write,FileShare.None)){
                if(input.Length<16)throw new IOException("Installer payload is missing.");
                input.Position=input.Length-16;byte[] footer=new byte[16];if(input.Read(footer,0,16)!=16||System.Text.Encoding.ASCII.GetString(footer,0,8)!="TLTSETUP")throw new IOException("Installer payload is invalid.");
                long remaining=BitConverter.ToInt64(footer,8);
                if(remaining<=0||remaining>input.Length-16||remaining>1024L*1024*1024)throw new IOException("Installer payload length is invalid.");
                input.Position=input.Length-16-remaining;
                using(var sha=SHA256.Create()){
                    byte[] buffer=new byte[1024*1024];
                    while(remaining>0){if(cancel)return ExitCode=1223;int count=input.Read(buffer,0,(int)Math.Min(buffer.Length,remaining));if(count==0)throw new IOException("Installer payload is incomplete.");sha.TransformBlock(buffer,0,count,null,0);output.Write(buffer,0,count);remaining-=count;}
                    sha.TransformFinalBlock(new byte[0],0,0);
                    if(BitConverter.ToString(sha.Hash).Replace("-","").ToLowerInvariant()!=SetupBuild.EngineHash)throw new IOException("Installer payload verification failed. Download setup again.");
                }
            }
            if(cancel)return ExitCode=1223;
            var start=new ProcessStartInfo(engine,"/S "+(update?"/UPDATE ":"")+"/D="+Root){UseShellExecute=false,CreateNoWindow=true};
            start.EnvironmentVariables["TLT_SETUP_STATUS"]=status;
            using(var process=Process.Start(start)){
                while(!process.WaitForExit(100)){
                    ReadProgress(status);
                    if(cancel&&Stage<3)File.WriteAllText(status+".cancel","");
                }
                ReadProgress(status);ExitCode=process.ExitCode;
            }
            if(ExitCode==1223)return ExitCode;
            if(ExitCode!=0)throw new IOException("Installation could not finish. Close Tech Lounge, check free space and try again. ");
            Stage=4;Percent=99;
            string installed=File.ReadAllText(Path.Combine(Root,"current.txt")).Trim();
            if(installed!=SetupBuild.Version)throw new IOException("Installed version did not match this setup package.");
            string folder=Path.Combine(Root,"versions",installed);
            Verify(Path.Combine(folder,"TechLoungeTweaks.exe"),SetupBuild.CoreHash);
            Verify(Path.Combine(folder,"TechLounge.exe"),SetupBuild.TrayHash);
            if(!File.Exists(Path.Combine(Root,"Uninstall.exe")))throw new IOException("Uninstaller is missing.");
            if(File.Exists(status+".warning"))Warning=File.ReadAllText(status+".warning");
            Percent=100;return ExitCode=0;
        }catch(Exception ex){Error=ex.Message;return ExitCode=1;}
        finally{Dispose();}
    }
    void ReadProgress(string path){
        try{using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite))using(var reader=new StreamReader(stream)){
            var fields=reader.ReadToEnd().Split('|');int stage,percent;
            if(fields.Length==2&&Int32.TryParse(fields[0],out stage)&&Int32.TryParse(fields[1],out percent)&&stage>=0&&stage<=4&&percent>=Percent&&percent<=98){Stage=stage;Percent=percent;}
        }}catch(IOException){}
    }
    static void Verify(string path,string expected){using(var sha=SHA256.Create())using(var input=File.OpenRead(path)){
        if(BitConverter.ToString(sha.ComputeHash(input)).Replace("-","").ToLowerInvariant()!=expected)throw new IOException("An installed file could not be verified. Run setup again.");
    }}
    public void Dispose(){try{if(Directory.Exists(cache))Directory.Delete(cache,true);}catch(IOException){}catch(UnauthorizedAccessException){}}
}

sealed class SoftButton:Control,IButtonControl {
    public Color Accent;
    public bool Primary,CloseButton;
    float hover,pressed;
    bool over,down;
    readonly System.Windows.Forms.Timer timer=new System.Windows.Forms.Timer{Interval=16};
    public DialogResult DialogResult{get;set;}
    public void NotifyDefault(bool value){Invalidate();}
    public void PerformClick(){if(Enabled&&Visible)OnClick(EventArgs.Empty);}
    public SoftButton(){SetStyle(ControlStyles.UserPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.AllPaintingInWmPaint|ControlStyles.Selectable,true);TabStop=true;AccessibleRole=AccessibleRole.PushButton;BackColor=Color.FromArgb(29,41,58);ForeColor=Color.FromArgb(235,242,252);Cursor=Cursors.Hand;Font=new Font("Segoe UI",10,FontStyle.Bold);timer.Tick+=(s,e)=>{hover+=((over?1:0)-hover)*.28f;pressed+=((down?1:0)-pressed)*.35f;if(Math.Abs(hover-(over?1:0))<.02&&Math.Abs(pressed-(down?1:0))<.02){hover=over?1:0;pressed=down?1:0;timer.Stop();}Invalidate();};}
    protected override void OnKeyDown(KeyEventArgs e){base.OnKeyDown(e);if(e.KeyCode==Keys.Space){down=true;Invalidate();e.Handled=true;}}
    protected override void OnKeyUp(KeyEventArgs e){base.OnKeyUp(e);if(e.KeyCode==Keys.Space){down=false;Invalidate();PerformClick();e.Handled=true;}}
    protected override void OnMouseEnter(EventArgs e){base.OnMouseEnter(e);over=true;if(SetupWindow.Motion)timer.Start();else{hover=1;Invalidate();}}
    protected override void OnMouseLeave(EventArgs e){base.OnMouseLeave(e);over=false;down=false;if(SetupWindow.Motion)timer.Start();else{hover=0;Invalidate();}}
    protected override void OnMouseDown(MouseEventArgs e){base.OnMouseDown(e);down=true;if(SetupWindow.Motion)timer.Start();else pressed=1;Invalidate();}
    protected override void OnMouseUp(MouseEventArgs e){base.OnMouseUp(e);down=false;if(SetupWindow.Motion)timer.Start();else pressed=0;Invalidate();}
    protected override void OnPaintBackground(PaintEventArgs e){e.Graphics.Clear(Color.FromArgb(29,41,58));}
    protected override void OnPaint(PaintEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;int inset=(int)Math.Round(pressed*2);var box=new Rectangle(inset,inset,Width-1-2*inset,Height-1-2*inset);
        Color fill=Primary?SetupWindow.Blend(Accent,Color.White,.07f*hover):Color.FromArgb((int)(20+hover*22),CloseButton?245:180,CloseButton?85:202,CloseButton?115:235);
        using(var p=SetupWindow.Round(box,11))using(var b=new SolidBrush(fill))e.Graphics.FillPath(b,p);
        TextRenderer.DrawText(e.Graphics,Text,Font,box,Enabled?ForeColor:Color.FromArgb(125,145,170),TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.NoPrefix);
        if(Focused&&ShowFocusCues)ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(box,-5,-5),ForeColor,BackColor);
    }
    protected override void Dispose(bool disposing){if(disposing){timer.Dispose();Font.Dispose();}base.Dispose(disposing);}
}

sealed class SetupWindow:Form {
    [DllImport("user32.dll")] static extern bool SystemParametersInfo(uint action,uint param,ref int result,uint flags);
    [DllImport("user32.dll")] static extern bool ReleaseCapture();
    [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr window,uint message,IntPtr wparam,IntPtr lparam);
    public static bool Motion {get{int value=1;return SystemParametersInfo(0x1042,0,ref value,0)&&value!=0;}}
    readonly Installation install;
    readonly bool animate=Motion;
    readonly bool solid;
    readonly Color accent;
    readonly SoftButton primary,secondary,minimise,close;
    readonly System.Windows.Forms.Timer frames=new System.Windows.Forms.Timer{Interval=16};
    readonly Stopwatch clock=new Stopwatch();
    string screen="welcome";
    float displayed;
    int previousStage=-1;
    long stageAt,hideAt;
    bool hiding,minimising,allowClose;
    int restingTop;
    readonly Font title=new Font("Segoe UI",30,FontStyle.Bold,GraphicsUnit.Pixel),body=new Font("Segoe UI",14,FontStyle.Regular,GraphicsUnit.Pixel),small=new Font("Segoe UI",12,FontStyle.Regular,GraphicsUnit.Pixel),bold=new Font("Segoe UI",14,FontStyle.Bold,GraphicsUnit.Pixel),brand=new Font("Segoe UI",15,FontStyle.Bold,GraphicsUnit.Pixel);
    static readonly string[] Titles={"Preparing your setup","Installing the desktop app","Adding bundled tools","Setting up quick actions","Checking everything is ready"};
    static readonly string[] Descriptions={"Checking the install location and unpacking the essentials.","Putting the full Tech Lounge toolkit in place.","Installing the tools included with your app. No extra download.","Creating your shortcuts and setting up delayed startup.","Verifying the installed app and tray companion."};
    public SetupWindow(Installation runner){
        install=runner;accent=ReadAccent();solid=SystemInformation.HighContrast;Text="Tech Lounge Tweaks Setup";AccessibleDescription="Install the desktop app, tray quick actions and automatic app updates. The tray starts three minutes after sign-in; this can be disabled in settings.";Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        AutoScaleMode=AutoScaleMode.Dpi;ClientSize=new Size(680,572);FormBorderStyle=FormBorderStyle.None;StartPosition=FormStartPosition.CenterScreen;BackColor=Color.FromArgb(28,39,55);DoubleBuffered=true;Font=body;
        primary=Button("Install",526,508,124,44,true,()=>{if(screen=="welcome"||screen=="error"||screen=="cancelled")BeginInstall();else if(screen=="complete")OpenApp();});
        secondary=Button("Cancel",402,508,112,44,false,()=>{if(screen=="progress")RequestCancel();else Dismiss(false);});
        minimise=Button("−",584,20,33,30,false,()=>Dismiss(true));minimise.AccessibleName="Minimise setup";
        close=Button("×",623,20,33,30,false,()=>{if(screen=="progress")RequestCancel();else Dismiss(false);});close.CloseButton=true;close.AccessibleName="Close setup";
        AcceptButton=primary;CancelButton=secondary;
        frames.Tick+=(s,e)=>TickFrame();clock.Start();
        FormClosing+=(s,e)=>{if(!allowClose&&screen=="progress"){e.Cancel=true;RequestCancel();}};
        Resize+=(s,e)=>{if(WindowState==FormWindowState.Normal&&Opacity<1&&!hiding){Opacity=1;Top=restingTop;}};
        MouseDown+=(s,e)=>{if(e.Button==MouseButtons.Left&&e.Y<80){ReleaseCapture();SendMessage(Handle,0xA1,new IntPtr(2),IntPtr.Zero);}};
        Shown+=(s,e)=>{restingTop=Top;};
    }
    static Color ReadAccent(){var names=new System.Collections.Generic.Dictionary<string,string>{{"blue","#2f7dff"},{"blurple","#5865f2"},{"purple","#8b5cf6"},{"red","#ff2d6b"},{"green","#16c98a"},{"cyan","#12b6cf"}};using(var k=Registry.CurrentUser.OpenSubKey(@"Software\TechLoungeTweaks")){string name=k==null?"blue":Convert.ToString(k.GetValue("Theme","blue"));return ColorTranslator.FromHtml(names.ContainsKey(name)?names[name]:names["blue"]);}}
    SoftButton Button(string text,int x,int y,int w,int h,bool main,Action action){var button=new SoftButton{Text=text,Accent=Blend(accent,Color.Black,.13f),Primary=main};button.SetBounds(x,y,w,h);button.Click+=(s,e)=>action();Controls.Add(button);return button;}
    public static Color Blend(Color a,Color b,float t){return Color.FromArgb((int)(a.R+(b.R-a.R)*t),(int)(a.G+(b.G-a.G)*t),(int)(a.B+(b.B-a.B)*t));}
    public static GraphicsPath Round(Rectangle r,int radius){var p=new GraphicsPath();int d=radius*2;p.AddArc(r.X,r.Y,d,d,180,90);p.AddArc(r.Right-d,r.Y,d,d,270,90);p.AddArc(r.Right-d,r.Bottom-d,d,d,0,90);p.AddArc(r.X,r.Bottom-d,d,d,90,90);p.CloseFigure();return p;}
    protected override void OnResize(EventArgs e){base.OnResize(e);if(Width>0&&Height>0)using(var path=Round(ClientRectangle,20)){var old=Region;Region=new Region(path);if(old!=null)old.Dispose();}}
    async void BeginInstall(){
        if(screen=="progress")return;
        // A runner owns exactly one engine invocation. Failed or cancelled setup
        // can be restarted by launching setup again, without overlapping work.
        screen="progress";primary.Visible=false;secondary.Text="Cancel";displayed=0;previousStage=-1;frames.Interval=animate?16:100;frames.Start();Invalidate();
        int result=await Task.Run(()=>install.Run());
        screen=result==0?"complete":result==1223?"cancelled":"error";frames.Stop();displayed=install.Percent;
        primary.Visible=result==0;primary.Text="Open app";secondary.Text="Done";secondary.Enabled=true;close.Enabled=true;Invalidate();
    }
    void RequestCancel(){if(install.Stage>=3){secondary.Text="Finishing…";secondary.Enabled=false;return;}install.Cancel();secondary.Text="Cancelling…";secondary.Enabled=false;Invalidate();}
    void OpenApp(){try{Process.Start(new ProcessStartInfo(Path.Combine(install.Root,"TechLounge.exe")){UseShellExecute=true});Dismiss(false);}catch(Exception ex){MessageBox.Show(this,ex.Message,"Tech Lounge",MessageBoxButtons.OK,MessageBoxIcon.Information);}}
    void Dismiss(bool minimiseWindow){
        if(hiding)return;restingTop=Top;minimising=minimiseWindow;
        if(!animate){if(minimiseWindow)WindowState=FormWindowState.Minimized;else{allowClose=true;Close();}return;}
        hiding=true;hideAt=clock.ElapsedMilliseconds;frames.Interval=16;frames.Start();
    }
    void TickFrame(){
        if(hiding){float t=Math.Min(1,(clock.ElapsedMilliseconds-hideAt)/180f);Opacity=1-t;Top=restingTop+(int)(12*t*t);if(t>=1){hiding=false;if(minimising){WindowState=FormWindowState.Minimized;Top=restingTop;Opacity=1;}else{allowClose=true;Close();return;}}}
        if(screen=="progress"){
            if(previousStage!=install.Stage){previousStage=install.Stage;stageAt=clock.ElapsedMilliseconds;AccessibleDescription=Titles[install.Stage]+". "+Descriptions[install.Stage];AccessibilityNotifyClients(AccessibleEvents.DescriptionChange,-1);}
            displayed=animate?displayed+(install.Percent-displayed)*.18f:install.Percent;
            if(!hiding)frames.Interval=WindowState==FormWindowState.Minimized?200:animate?16:100;
            if(WindowState!=FormWindowState.Minimized)Invalidate(new Rectangle(36,228,608,250));
        }else if(!hiding)frames.Stop();
    }
    void TextLine(Graphics g,string text,Font font,int x,int y,int width,int height,Color color){using(var brush=new SolidBrush(color))using(var format=new StringFormat{Trimming=StringTrimming.EllipsisCharacter})g.DrawString(text,font,brush,new RectangleF(x,y,width,height),format);}
    void Surface(Graphics g,Rectangle r,int radius,Color color){using(var p=Round(r,radius))using(var b=new SolidBrush(color))g.FillPath(b,p);}
    void Sliders(Graphics g,Rectangle r){using(var p=new Pen(Color.FromArgb(215,235,255),2.5f)){p.StartCap=p.EndCap=LineCap.Round;for(int i=0;i<3;i++){float y=r.Top+8+i*11;g.DrawLine(p,r.Left+3,y,r.Right-3,y);float x=r.Left+(i==1?25:12);using(var thick=new Pen(p.Color,4)){thick.StartCap=thick.EndCap=LineCap.Round;g.DrawLine(thick,x,y-4,x,y+4);}}}}
    protected override void OnPaint(PaintEventArgs e){
        base.OnPaint(e);var g=e.Graphics;var saved=g.Save();g.SmoothingMode=SmoothingMode.AntiAlias;
        // Paint in logical pixels so the owner-drawn content follows Windows DPI.
        float scale=ClientSize.Width/680f;g.ScaleTransform(scale,scale);

        using(var b=new LinearGradientBrush(new Rectangle(0,0,680,572),Blend(Color.FromArgb(27,39,56),accent,solid?.08f:.22f),Color.FromArgb(27,39,56),45))g.FillRectangle(b,0,0,680,572);
        var white=Color.FromArgb(237,242,252);var muted=Color.FromArgb(182,195,217);
        Surface(g,new Rectangle(30,21,32,32),10,Color.FromArgb(50,accent));Sliders(g,new Rectangle(35,23,22,27));
        TextLine(g,"Tech Lounge",brand,74,21,220,24,white);TextLine(g,"S E T U P",small,74,44,220,20,muted);
        Surface(g,new Rectangle(40,110,76,76),23,screen=="complete"?Color.FromArgb(33,75,76):accent);
        if(screen=="complete")TextLine(g,"✓",title,60,125,50,55,Color.FromArgb(137,223,190));else Sliders(g,new Rectangle(57,128,42,42));
        string heading=screen=="welcome"?"Install Tech Lounge Tweaks":screen=="progress"?"Installing Tech Lounge.":screen=="complete"?"You’re all set.":screen=="cancelled"?"Installation cancelled.":"Setup needs your attention.";
        string subtitle=screen=="welcome"?"Your Windows toolkit, always within reach.":screen=="progress"?"Setting up Tech Lounge and your tray companion.":screen=="complete"?"Tech Lounge is ready when you are.":"You can run setup again when you’re ready.";
        TextLine(g,heading,title,137,115,510,48,white);TextLine(g,subtitle,body,139,165,490,42,muted);
        if(screen=="welcome"){
            Surface(g,new Rectangle(40,222,600,53),14,Color.FromArgb(8,Color.White));
            TextLine(g,"▣  Full desktop app",bold,57,239,185,24,white);TextLine(g,"ϟ  Tray quick actions",bold,246,239,190,24,white);TextLine(g,"Automatic app updates",bold,446,239,190,24,white);
            Surface(g,new Rectangle(40,296,600,73),13,Color.FromArgb(10,Color.White));TextLine(g,"Install location",small,58,309,550,20,muted);TextLine(g,install.Root,small,58,336,555,25,white);
            TextLine(g,"Ready after sign-in",bold,40,393,590,25,white);TextLine(g,"The tray starts quietly, three minutes after sign-in.\nYou can turn this off in app settings.",small,40,420,590,46,muted);
        }else if(screen=="progress"){
            int stage=Math.Max(0,Math.Min(4,install.Stage));Surface(g,new Rectangle(40,228,600,231),15,Color.FromArgb(9,Color.White));
            TextLine(g,"STEP "+(stage+1)+" OF 5",small,62,246,500,22,Color.FromArgb(166,204,255));
            TextLine(g,install.CancelRequested?"Cancelling safely…":Titles[stage],bold,62,281,480,28,white);TextLine(g,install.Percent+"%",body,573,281,50,28,Color.FromArgb(166,204,255));
            Surface(g,new Rectangle(62,322,556,7),3,Color.FromArgb(20,Color.White));int width=(int)(556*displayed/100);
            if(width>6){Surface(g,new Rectangle(62,322,width,7),3,accent);if(animate){var old=g.Clip;g.SetClip(new Rectangle(62,322,width,7));float x=62+(clock.ElapsedMilliseconds%2200)/2200f*(width+100)-100;using(var shine=new LinearGradientBrush(new RectangleF(x,322,100,7),Color.Transparent,Color.FromArgb(130,Color.White),0f))g.FillRectangle(shine,x,322,100,7);g.Clip=old;old.Dispose();}}
            TextLine(g,Descriptions[stage],small,62,344,550,32,muted);
            int shift=animate?(int)(6*Math.Max(0,1-(clock.ElapsedMilliseconds-stageAt)/250f)):0;
            for(int i=Math.Max(0,stage-1);i<=stage;i++)TextLine(g,(i<stage?"✓  ":"•  ")+Titles[i]+(i<stage?" · Complete":""),small,62,388+(i-Math.Max(0,stage-1))*27+shift,550,25,i==stage?white:muted);
        }else if(screen=="complete"){
            TextLine(g,"✓   Desktop app installed\n\n✓   Quick actions available in your system tray\n\n✓   Automatic app updates ready",body,43,235,590,135,white);
            TextLine(g,install.Warning??"Open the app now, or find Tech Lounge in your Start menu.",body,43,403,590,60,muted);
        }else TextLine(g,install.Error??"Setup stopped. You can run it again when you’re ready.",body,43,250,590,170,white);
        using(var shade=new SolidBrush(Color.FromArgb(25,8,17,30)))g.FillRectangle(shade,0,488,680,84);
        TextLine(g,screen=="progress"?"Installing on this PC":"Windows 11 · 64-bit",small,30,524,300,25,muted);
        g.Restore(saved);
    }
    protected override void Dispose(bool disposing){if(disposing){frames.Dispose();title.Dispose();body.Dispose();small.Dispose();bold.Dispose();brand.Dispose();}base.Dispose(disposing);}
}
}
