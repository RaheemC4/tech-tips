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
    readonly Form window;readonly Control body;int baseLeft;readonly Action layout;readonly Func<bool> windowMoving;
    readonly Timer frames=new Timer{Interval=15};readonly Stopwatch clock=new Stopwatch();
    Rectangle from,target;int startOffset;bool disposed,pausedForClose,waiting;
    internal bool Running {get{return frames.Enabled;}}
    internal int Offset {get{return body.Left-baseLeft;}}
    internal TrayPageMotion(Form window,Control body,int baseLeft,Action layout,Func<bool> windowMoving){
        this.window=window;this.body=body;this.baseLeft=baseLeft;this.layout=layout;this.windowMoving=windowMoving;
        frames.Tick+=(s,e)=>Tick();window.FormClosing+=(s,e)=>{pausedForClose=Running;Pause();};window.Disposed+=(s,e)=>Dispose();
    }
    internal void SetBaseLeft(int value){baseLeft=value;}
    internal void Pause(){frames.Stop();}
    internal void Settle(){frames.Stop();Apply(1);}
    internal void Start(Rectangle previous,Rectangle destination,int offset,bool animate){
        frames.Stop();pausedForClose=false;waiting=false;from=previous;target=destination;startOffset=offset;
        if(!animate){Apply(1);return;}
        Apply(0);clock.Restart();frames.Start();
    }
    internal void Resume(){if(!pausedForClose||disposed)return;pausedForClose=false;from=window.Bounds;startOffset=Offset;waiting=true;clock.Restart();frames.Start();}
    void Tick(){
        if(waiting){if(windowMoving())return;waiting=false;from=window.Bounds;startOffset=Offset;clock.Restart();}
        double t=Math.Min(1,clock.Elapsed.TotalMilliseconds/110.0);
        Apply(1-(1-t)*(1-t));
        if(t==1){frames.Stop();clock.Stop();}
    }
    void Apply(double progress){
        int height=(int)Math.Round(from.Height+(target.Height-from.Height)*progress);
        int bottom=(int)Math.Round(from.Bottom+(target.Bottom-from.Bottom)*progress);
        int left=(int)Math.Round(from.Left+(target.Left-from.Left)*progress);
        window.Bounds=new Rectangle(left,bottom-height,target.Width,height);
        body.Left=baseLeft+(int)Math.Round(startOffset*(1-progress));layout();TrayRedrawBatch.Paint(window);
    }
    public void Dispose(){if(disposed)return;disposed=true;frames.Stop();frames.Dispose();}
}
}
