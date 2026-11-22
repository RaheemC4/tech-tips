using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace TechLounge {
sealed class PopupMotion:IDisposable {
    [DllImport("user32.dll")] static extern bool SystemParametersInfo(uint action,uint param,out bool value,uint flags);
    readonly Form window;readonly Timer frames=new Timer{Interval=15};readonly Stopwatch clock=new Stopwatch();
    readonly bool animate;
    double startOpacity;bool shown,closing,allowClose,disposed;
    internal bool Running {get{return frames.Enabled;}}
    internal static bool Enabled(){bool enabled;return SystemParametersInfo(0x1042,0,out enabled,0)&&enabled;}
    internal PopupMotion(Form window,bool animate){
        this.window=window;this.animate=animate;
        if(animate)window.Opacity=0;
        frames.Tick+=(s,e)=>Tick();
        window.FormClosing+=OnClosing;
        window.Disposed+=(s,e)=>Dispose();
    }
    internal void Show(){
        shown=true;
        if(animate)Start(false);
    }
    internal void Reopen(){if(closing&&!disposed){allowClose=false;Start(false);}}
    internal void Settle(){
        if(!shown||closing||disposed)return;
        frames.Stop();clock.Stop();if(window.Opacity!=1)window.Opacity=1;
    }
    void Start(bool leaving){
        closing=leaving;startOpacity=window.Opacity;
        clock.Restart();frames.Start();
    }
    void OnClosing(object sender,FormClosingEventArgs e){
        if(allowClose||!animate||e.CloseReason!=CloseReason.UserClosing){frames.Stop();return;}
        e.Cancel=true;
        if(!closing)Start(true);
    }
    void Tick(){
        double t=Math.Min(1,clock.Elapsed.TotalMilliseconds/(closing?85:110));
        double progress=1-(1-t)*(1-t);
        window.Opacity=startOpacity+((closing?0:1)-startOpacity)*progress;
        if(t<1)return;
        frames.Stop();clock.Stop();
        if(closing){allowClose=true;window.Close();}
    }
    public void Dispose(){if(disposed)return;disposed=true;frames.Stop();frames.Dispose();clock.Stop();}
}
}
