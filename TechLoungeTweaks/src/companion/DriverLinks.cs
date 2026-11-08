using System;
namespace TechLounge {
static class DriverLinks {
    internal static string SupportPage(string vendor){
        switch(vendor){
            case "NVIDIA":return "https://www.nvidia.com/Download/index.aspx";
            case "AMD":return "https://www.amd.com/en/support/download/drivers.html";
            case "Intel":return "https://www.intel.com/content/www/us/en/download-center/home.html";
            default:return null;
        }
    }
    internal static string UpdateUrl(System.Collections.Generic.Dictionary<string,object> gpu){
        if(Convert.ToString(gpu["status"])!="update")return null;
        string vendor=gpu.ContainsKey("vendor")?Convert.ToString(gpu["vendor"]):"",url=gpu.ContainsKey("url")?Convert.ToString(gpu["url"]):"";
        return IsOfficial(url,vendor)?url:SupportPage(vendor);
    }
    internal static bool IsOfficial(string value,string vendor){
        Uri uri;if(!Uri.TryCreate(value,UriKind.Absolute,out uri)||uri.Scheme!="https"||!uri.IsDefaultPort||uri.UserInfo!="")return false;
        string domain=vendor=="NVIDIA"?"nvidia.com":vendor=="AMD"?"amd.com":vendor=="Intel"?"intel.com":null;
        return domain!=null&&(uri.Host.Equals(domain,StringComparison.OrdinalIgnoreCase)||uri.Host.EndsWith("."+domain,StringComparison.OrdinalIgnoreCase));
    }
}
}
