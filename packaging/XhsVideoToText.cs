using System;
using System.Diagnostics;
using System.IO;
using System.Text;

internal static class Program
{
    private static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        string baseDir = AppContext.BaseDirectory;
        string userHome = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        string psScript = Path.Combine(baseDir, "xhs-video-to-text.ps1");
        if (!File.Exists(psScript))
        {
            psScript = Path.Combine(userHome, "xhs-video-to-text.ps1");
        }
        if (!File.Exists(psScript))
        {
            Console.WriteLine("\u672A\u627E\u5230\u811A\u672C: " + psScript);
            Pause();
            return 1;
        }

        string url = args.Length > 0 ? args[0].Trim() : "";
        if (string.IsNullOrWhiteSpace(url))
        {
            Console.Write("\u8BF7\u8F93\u5165\u5C0F\u7EA2\u4E66\u5206\u4EAB\u94FE\u63A5\uFF0C\u7136\u540E\u6309\u56DE\u8F66: ");
            url = (Console.ReadLine() ?? "").Trim();
        }

        if (string.IsNullOrWhiteSpace(url))
        {
            Console.WriteLine("\u6CA1\u6709\u8F93\u5165\u94FE\u63A5\u3002");
            Pause();
            return 1;
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File \"" + psScript + "\" -Url \"" + url.Replace("\"", "\\\"") + "\" -Local -LocalModel medium -LocalLanguage zh",
            UseShellExecute = false,
        };

        try
        {
            using (var process = Process.Start(startInfo))
            {
                if (process == null)
                {
                    Console.WriteLine("\u542F\u52A8\u5931\u8D25\u3002");
                    Pause();
                    return 1;
                }

                process.WaitForExit();
                if (process.ExitCode != 0)
                {
                    Console.WriteLine();
                    Console.WriteLine("\u5904\u7406\u7ED3\u675F\uFF0C\u4F46\u6709\u62A5\u9519\u3002");
                    Pause();
                    return process.ExitCode;
                }
            }

            Console.WriteLine();
            Console.WriteLine("\u5904\u7406\u5B8C\u6210\u3002");
            Pause();
            return 0;
        }
        catch (Exception ex)
        {
            Console.WriteLine("\u542F\u52A8\u5931\u8D25: " + ex.Message);
            Pause();
            return 1;
        }
    }

    private static void Pause()
    {
        if (!Console.IsInputRedirected)
        {
            Console.Write("\u6309\u56DE\u8F66\u9000\u51FA...");
            Console.ReadLine();
        }
    }
}
