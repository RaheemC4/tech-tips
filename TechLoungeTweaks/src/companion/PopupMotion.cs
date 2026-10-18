using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace TechLounge {
sealed class PopupMotion:IDisposable {
    [DllImport("user32.dll")] static extern bool SystemParametersInfo(uint action,uint param,out bool value,uint flags);
    readonly Form window;readonly Timer frames=new Timer{Interval=15};readonly Stopwatch clock=new Stopwatch();
    readonly int distance;readonly bool animate;
    int restingTop,startTop;double startOpacity;bool closing,allowClose,disposed;
    internal bool Running {get{return frames.Enabled;}}
    internal static bool Enabled(){bool enabled;return SystemParametersInfo(0x1042,0,out enabled,0)&&enabled;}
    internal PopupMotion(Form window,int distance,bool animate){
        this.window=window;this.distance=distance;this.animate=animate;
        if(animate)window.Opacity=0;
        frames.Tick+=(s,e)=>Tick();
        window.FormClosing+=OnClosing;
        window.Disposed+=(s,e)=>Dispose();
    }
    internal void Show(){
        restingTop=window.Top;
        if(!animate)return;
        window.Top=restingTop+distance;
        Start(false);
    }
    internal void Reopen(){if(closing&&!disposed){allowClose=false;Start(false);}}
    internal void Settle(){
        if(closing||disposed)return;
        frames.Stop();clock.Stop();window.Top=restingTop;window.Opacity=1;
    }
    internal void Reanchor(){restingTop=window.Top;}
    void Start(bool leaving){
        closing=leaving;startTop=window.Top;startOpacity=window.Opacity;
        clock.Restart();frames.Start();
    }
    void OnClosing(object sender,FormClosingEventArgs e){
        if(allowClose||!animate||e.CloseReason!=CloseReason.UserClosing){frames.Stop();return;}
        e.Cancel=true;
        if(!closing)Start(true);
    }
    void Tick(){
        double milliseconds=clock.Elapsed.TotalMilliseconds;
        double t=Math.Min(1,milliseconds/(closing?150:320));
        if(closing){
            window.Top=(int)Math.Round(startTop+(restingTop+distance*.65-startTop)*t*t);
            window.Opacity=startOpacity*(1-t*t);
        }else{
            double spring=1-Math.Exp(-7*t)*Math.Cos(10*t);
            window.Top=(int)Math.Round(startTop+(restingTop-startTop)*spring);
            double fade=Math.Min(1,milliseconds/180);
            window.Opacity=startOpacity+(1-startOpacity)*(1-Math.Pow(1-fade,3));
        }
        if(t<1)return;
        frames.Stop();clock.Stop();
        if(closing){allowClose=true;window.Close();}
        else{window.Top=restingTop;window.Opacity=1;}
    }
    public void Dispose(){if(disposed)return;disposed=true;frames.Stop();frames.Dispose();clock.Stop();}
}
}
