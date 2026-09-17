using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace SWAI
{
    /// <summary>
    /// SolidWorks COM API 辅助类。
    /// 
    /// 封装常用的 SolidWorks 操作：
    /// - 连接/断开 SW 实例
    /// - 执行 VBA 宏
    /// - 获取/创建文档
    /// - 错误处理
    /// 
    /// 注意：所有方法需要在 SolidWorks 主线程中调用（通过控件事件）。
    /// </summary>
    public static class SwApiHelper
    {
        private static SldWorks _swApp;

        #region 连接管理

        /// <summary>
        /// 获取当前 SolidWorks 应用程序实例。
        /// 如果尚未连接或已断开，尝试重新获取。
        /// </summary>
        /// <returns>SolidWorks 应用实例，或 null</returns>
        public static SldWorks GetSwApp()
        {
            if (_swApp == null)
            {
                try
                {
                    _swApp = (SldWorks)Marshal.GetActiveObject("SldWorks.Application");
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine("[SwApiHelper] GetSwApp failed: " + ex.Message);
                    return null;
                }
            }
            return _swApp;
        }

        /// <summary>
        /// 确保 SolidWorks 实例可见。
        /// </summary>
        public static void EnsureVisible()
        {
            var app = GetSwApp();
            if (app != null)
            {
                app.Visible = true;
            }
        }

        /// <summary>
        /// 释放对 SolidWorks 实例的引用。
        /// </summary>
        public static void Release()
        {
            try
            {
                if (_swApp != null)
                {
                    Marshal.ReleaseComObject(_swApp);
                    _swApp = null;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SwApiHelper] Release failed: " + ex.Message);
            }
        }

        #endregion

        #region 文档操作

        /// <summary>
        /// 获取当前激活的文档。
        /// </summary>
        /// <returns>当前文档，或 null</returns>
        public static ModelDoc2 GetActiveDoc()
        {
            try
            {
                var app = GetSwApp();
                if (app == null) return null;

                return (ModelDoc2)app.ActiveDoc;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SwApiHelper] GetActiveDoc failed: " + ex.Message);
                return null;
            }
        }

        /// <summary>
        /// 创建新的零件文档。
        /// </summary>
        /// <returns>新零件文档，或 null</returns>
        public static ModelDoc2 CreateNewPart()
        {
            try
            {
                var app = GetSwApp();
                if (app == null) return null;

                int docType = (int)swDocumentTypes_e.swDocPART;
                // 现代 API：GetDocumentTemplate(Mode, TemplateName, PaperSize, Width, Height)
                string template = app.GetDocumentTemplate(docType, "", 0, 0, 0);

                if (string.IsNullOrEmpty(template))
                {
                    // 尝试默认模板路径
                    string swPath = System.Environment.GetFolderPath(System.Environment.SpecialFolder.ProgramFiles);
                    template = Path.Combine(swPath,
                        "SolidWorks Corp", "SolidWorks",
                        "lang", "chinese-simplified",
                        "Templates", "gb_part.prtdot");
                }

                return (ModelDoc2)app.NewDocument(template, 0, 0.0, 0.0);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SwApiHelper] CreateNewPart failed: " + ex.Message);
                return null;
            }
        }

        /// <summary>
        /// 保存当前文档。
        /// </summary>
        /// <param name="filePath">保存路径，为 null 时使用原路径</param>
        /// <returns>是否保存成功</returns>
        public static bool SaveDocument(string filePath = null)
        {
            try
            {
                var doc = GetActiveDoc();
                if (doc == null) return false;

                if (!string.IsNullOrEmpty(filePath))
                {
                    string dir = Path.GetDirectoryName(filePath);
                    if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                    {
                        Directory.CreateDirectory(dir);
                    }

                    // 现代 API：SaveAs3(NewName, SaveAsVersion, Options)
                    int result = doc.SaveAs3(
                        filePath,
                        (int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                        (int)swSaveAsOptions_e.swSaveAsOptions_Silent);
                    return result == 0;
                }
                else
                {
                    // 现代 API：Save2(Silent) 返回错误码，0 = 成功
                    return doc.Save2(true) == 0;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SwApiHelper] SaveDocument failed: " + ex.Message);
                return false;
            }
        }

        #endregion

        #region VBA 宏执行（cscript/VBS 通道）

        /// <summary>
        /// 最近一次宏执行的 cscript 输出（供 UI 日志展示）。
        /// </summary>
        public static string LastMacroOutput { get; private set; } = "";

        /// <summary>
        /// 在 SolidWorks 中执行 VBA 宏字符串（异步包装，不阻塞 UI 线程）。
        /// </summary>
        public static async Task<bool> RunMacroAsync(string code, string macroPath = null)
        {
            return await Task.Run(() => RunMacro(code, macroPath));
        }

        /// <summary>
        /// 在 SolidWorks 中执行 VBA 宏字符串。
        ///
        /// 通道：VBA -> VBS 转换 -> cscript.exe 外部执行（GetObject 连接运行中的 SW）。
        /// 不使用 RunMacro2：它只接受 .swp/.swb 宏工程，无法打开裸 .bas
        /// （会弹出"无法打开宏文件"；SW2022 E2E 实测，见 tools/vba_to_vbs.py）。
        /// </summary>
        /// <param name="code">VBA 宏代码</param>
        /// <param name="macroPath">可选：指定输出路径（自动改后缀为 .vbs）</param>
        /// <returns>是否执行成功（以 MACRO_DONE 哨兵判定）</returns>
        public static bool RunMacro(string code, string macroPath = null)
        {
            try
            {
                string vbs = ConvertVbaToVbs(code);

                string tempPath = macroPath;
                if (string.IsNullOrEmpty(tempPath))
                {
                    tempPath = Path.Combine(Path.GetTempPath(), "SWAI_TempMacro.vbs");
                }
                else
                {
                    tempPath = Path.ChangeExtension(macroPath, ".vbs") ?? macroPath;
                }

                // cscript 按 ANSI 读取 .vbs，用系统代码页写入
                File.WriteAllText(tempPath, vbs, System.Text.Encoding.Default);

                var psi = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "cscript.exe",
                    Arguments = "//nologo \"" + tempPath + "\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };

                using (var proc = System.Diagnostics.Process.Start(psi))
                {
                    string output = proc.StandardOutput.ReadToEnd();
                    if (!proc.WaitForExit(300000))
                    {
                        try { proc.Kill(); } catch { }
                        System.Diagnostics.Debug.WriteLine("[SwApiHelper] cscript timeout (300s)");
                        LastMacroOutput = "cscript 超时（300s）";
                        return false;
                    }

                    LastMacroOutput = output.Trim();
                    System.Diagnostics.Debug.WriteLine("[SwApiHelper] cscript: " + LastMacroOutput);

                    return LastMacroOutput.IndexOf("MACRO_DONE", StringComparison.Ordinal) >= 0;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SwApiHelper] RunMacro failed: " + ex.Message);
                LastMacroOutput = ex.Message;
                return false;
            }
        }

        /// <summary>
        /// 从已有宏文件运行（.bas 源码或 .vbs 均可，统一走 VBS 通道）。
        /// </summary>
        public static bool RunMacroFile(string macroFilePath)
        {
            if (!File.Exists(macroFilePath))
            {
                System.Diagnostics.Debug.WriteLine("[SwApiHelper] Macro file not found: " + macroFilePath);
                return false;
            }

            string code = File.ReadAllText(macroFilePath, System.Text.Encoding.Default);
            return RunMacro(code, macroFilePath);
        }

        /// <summary>
        /// VBA -> VBS 翻译器（与 tools/vba_to_vbs.py 规则一致，SW2022 E2E 实测配方）：
        ///  1. 丢弃 Attribute / Option Explicit 行
        ///  2. Application.SldWorks -> GetObject(, "SldWorks.Application")
        ///  3. swApp.NewDocument(...) -> swApp.NewPart()   （外部 NewDocument("") 返回 Nothing）
        ///  4. VBA 数字字面量后缀 0# / 1.5# / 2! -> 无后缀
        ///  5. Dim x(0 To N) As T -> Dim x(N)；Dim x As T -> Dim x
        ///  6. MsgBox / Debug.Print 语句（含 _ 续行）注释化
        ///  7. Next i -> Next
        ///  8. 尾部追加错误陷阱 + MACRO_DONE 哨兵
        /// </summary>
        private static string ConvertVbaToVbs(string vba)
        {
            var sb = new System.Text.StringBuilder();
            bool inMsgbox = false;

            foreach (var raw in vba.Replace("\r\n", "\n").Split('\n'))
            {
                string s = raw.TrimEnd();

                if (inMsgbox)
                {
                    sb.AppendLine("' [swai] " + s);
                    if (!s.TrimEnd().EndsWith("_")) inMsgbox = false;
                    continue;
                }

                if (System.Text.RegularExpressions.Regex.IsMatch(s, @"^\s*Attribute\s+VB_Name")) continue;
                if (System.Text.RegularExpressions.Regex.IsMatch(s, @"^\s*Option\s+Explicit")) continue;

                if (System.Text.RegularExpressions.Regex.IsMatch(s, @"^\s*MsgBox\b", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                {
                    sb.AppendLine("' [swai] " + s);
                    if (s.TrimEnd().EndsWith("_")) inMsgbox = true;
                    continue;
                }

                string t = s;
                t = System.Text.RegularExpressions.Regex.Replace(
                    t, @"Application\.SldWorks", "GetObject(, \"SldWorks.Application\")");
                t = System.Text.RegularExpressions.Regex.Replace(
                    t, @"swApp\.NewDocument\s*\([^)]*\)", "swApp.NewPart()");
                t = System.Text.RegularExpressions.Regex.Replace(t, @"(\d(?:\.\d+)?)\s*[#!]", "$1");
                t = System.Text.RegularExpressions.Regex.Replace(
                    t, @"Dim\s+(\w+)\s*\(\s*\d+\s+To\s+(\d+)\s*\)\s+As\s+\w+",
                    "Dim $1($2)", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                t = System.Text.RegularExpressions.Regex.Replace(
                    t, @"Dim\s+(\w+)\s+As\s+\w+", "Dim $1", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                t = System.Text.RegularExpressions.Regex.Replace(
                    t, @"^(\s*)Next\s+\w+\s*$", "$1Next", System.Text.RegularExpressions.RegexOptions.IgnoreCase);

                if (System.Text.RegularExpressions.Regex.IsMatch(t, @"^\s*Debug\.Print", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                {
                    t = "' [swai] " + t;
                }

                sb.AppendLine(t);
            }

            sb.AppendLine();
            sb.AppendLine("On Error Resume Next");
            sb.AppendLine("main");
            sb.AppendLine("If Err.Number <> 0 Then");
            sb.AppendLine("    WScript.Echo \"MACRO_ERROR \" & Err.Number & \": \" & Err.Description");
            sb.AppendLine("    WScript.Quit 1");
            sb.AppendLine("End If");
            sb.AppendLine("WScript.Echo \"MACRO_DONE\"");

            return sb.ToString();
        }

        #endregion

        #region 错误处理

        /// <summary>
        /// 获取 SolidWorks 最后一次错误码（通过 GetLastError 不可用时的兜底）。
        /// </summary>
        public static string GetLastError()
        {
            try
            {
                var app = GetSwApp();
                if (app == null) return "SolidWorks not available";
                return "LastError unavailable (use debugger) — app=" + (app.Visible ? "visible" : "hidden");
            }
            catch (Exception ex)
            {
                return ex.Message;
            }
        }

        #endregion
    }
}
