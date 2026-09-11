using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows.Forms;

// Small launcher using the Windows .NET Framework; all app files stay in _internal.
internal static class PortableLauncher
{
    private static string Quote(string value)
    {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') result.Append('\\', slashes * 2 + 1);
            else result.Append('\\', slashes);
            result.Append(c);
            slashes = 0;
        }
        result.Append('\\', slashes * 2);
        return result.Append('"').ToString();
    }

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string target = Path.Combine(root, "_internal", "TechLoungeTweaks.exe");
            if (!File.Exists(target)) throw new FileNotFoundException("Extract the entire ZIP before opening TechLoungeTweaks. The _internal folder is missing.");
            var arguments = new StringBuilder();
            foreach (string arg in args) { if (arguments.Length > 0) arguments.Append(' '); arguments.Append(Quote(arg)); }
            Process.Start(new ProcessStartInfo(target, arguments.ToString()) { UseShellExecute = true, WorkingDirectory = root });
            return 0;
        }
        catch (System.ComponentModel.Win32Exception error)
        {
            if (error.NativeErrorCode == 1223) return 1; // User cancelled administrator approval.
            MessageBox.Show(error.Message, "TechLoungeTweaks could not open");
            return 1;
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "TechLoungeTweaks could not open");
            return 1;
        }
    }
}
