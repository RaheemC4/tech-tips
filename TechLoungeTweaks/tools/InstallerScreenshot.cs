using System;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
class InstallerScreenshot {
 [STAThread] static int Main(string[] args){
  Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
  var assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));
  string root=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","TechLoungeTweaks");
  using(var runner=(IDisposable)Activator.CreateInstance(assembly.GetType("TechLoungeSetup.Installation",true),new object[]{root,false}))
  using(var form=(Form)Activator.CreateInstance(assembly.GetType("TechLoungeSetup.SetupWindow",true),new object[]{runner}))
  using(var timer=new Timer{Interval=250}){
   timer.Tick+=(s,e)=>{timer.Stop();using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,form.ClientRectangle);bitmap.Save(args[1],System.Drawing.Imaging.ImageFormat.Png);}form.Close();};
   form.Shown+=(s,e)=>timer.Start();Application.Run(form);
  }return 0;
 }
}
