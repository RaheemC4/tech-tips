using System;using System.Diagnostics;using System.Drawing;using System.Runtime.InteropServices;using System.Windows.Forms;
namespace TechLounge {
// Freeze native painting while a page's controls are replaced, not its input.
sealed class TrayRedrawBatch:IDisposable {
    [DllImport("user32.dll")]static extern IntPtr SendMessage(IntPtr h,int m,IntPtr w,IntPtr l);
    [DllImport("user32.dll")]static extern bool RedrawWindow(IntPtr h,IntPtr r,IntPtr region,uint flags);
    readonly Control window,body;readonly bool active;
    internal TrayRedrawBatch(Control window,Control body){this.window=window;this.body=body;active=window.IsHandleCreated&&window.Visible;if(active){SendMessage(window.Handle,11,IntPtr.Zero,IntPtr.Zero);if(body.IsHandleCreated)SendMessage(body.Handle,11,IntPtr.Zero,IntPtr.Zero);}}
    internal static void Paint(Control window){if(!window.IsDisposed&&window.IsHandleCreated)RedrawWindow(window.Handle,IntPtr.Zero,IntPtr.Zero,0x185);}
    public void Dispose(){if(!active||window.IsDisposed)return;if(body.IsHandleCreated)SendMessage(body.Handle,11,new IntPtr(1),IntPtr.Zero);SendMessage(window.Handle,11,new IntPtr(1),IntPtr.Zero);Paint(window);}
}
sealed class TrayPageMotion:IDisposable {
    readonly Form window;readonly Control body;readonly int baseLeft;readonly Action layout;readonly Func<bool> windowMoving;
    readonly Timer frames=new Timer{Interval=15};readonly Stopwatch clock=new Stopwatch();
    Rectangle from,target;int startOffset;bool disposed,pausedForClose,waiting;
    internal bool Running {get{return frames.Enabled;}}
    internal int Offset {get{return body.Left-baseLeft;}}
    internal TrayPageMotion(Form window,Control body,int baseLeft,Action layout,Func<bool> windowMoving){
        this.window=window;this.body=body;this.baseLeft=baseLeft;this.layout=layout;this.windowMoving=windowMoving;
        frames.Tick+=(s,e)=>Tick();window.FormClosing+=(s,e)=>{pausedForClose=Running;Pause();};window.Disposed+=(s,e)=>Dispose();
    }
    internal void Pause(){frames.Stop();}
    internal void Start(Rectangle previous,Rectangle destination,int offset,bool animate){
        frames.Stop();pausedForClose=false;waiting=false;from=previous;target=destination;startOffset=offset;
        if(!animate){Apply(1);return;}
        Apply(0);clock.Restart();frames.Start();
    }
    internal void Resume(){if(!pausedForClose||disposed)return;pausedForClose=false;from=window.Bounds;startOffset=Offset;waiting=true;clock.Restart();frames.Start();}
    void Tick(){
        if(waiting){if(windowMoving())return;waiting=false;from=window.Bounds;startOffset=Offset;clock.Restart();}
        double t=Math.Min(1,clock.Elapsed.TotalMilliseconds/300.0);
        double spring=t==1?1:1-Math.Exp(-7*t)*Math.Cos(10*t);
        Apply(spring);
        if(t==1){frames.Stop();clock.Stop();}
    }
    void Apply(double progress){
        window.Bounds=new Rectangle((int)Math.Round(from.Left+(target.Left-from.Left)*progress),(int)Math.Round(from.Top+(target.Top-from.Top)*progress),target.Width,(int)Math.Round(from.Height+(target.Height-from.Height)*progress));
        body.Left=baseLeft+(int)Math.Round(startOffset*(1-progress));layout();TrayRedrawBatch.Paint(window);
    }
    public void Dispose(){if(disposed)return;disposed=true;frames.Stop();frames.Dispose();}
}
}
