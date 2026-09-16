using System;
using System.Runtime.InteropServices;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swpublished;

namespace SWAI
{
    /// <summary>
    /// SWAI SolidWorks 插件主入口
    /// 
    /// 注册方式（管理员终端）：
    ///   regasm /codebase SWAIAddin.dll
    ///   或在安装时由安装程序自动注册。
    /// </summary>
    [Guid("A1B2C3D4-E5F6-7890-ABCD-EF1234567891")]
    [ComVisible(true)]
    [ProgId("SWAI.Addin")]
    public class SWAIAddin : ISwAddin
    {
        #region 私有字段

        private SldWorks _swApp;
        private int _addinId;
        private TaskPaneControl _taskPane;
        private TaskpaneView _taskPaneView;
        private bool _connected = false;

        // 命令 ID
        private const int CMD_OPEN_PANEL = 1;

        #endregion

        #region 诊断日志

        private static readonly string LogPath = @"C:\ProgramData\SWAIPlugin\addin_load.log";

        private static void Log(string msg)
        {
            try
            {
                System.IO.File.AppendAllText(LogPath,
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " [pid " +
                    System.Diagnostics.Process.GetCurrentProcess().Id + "] " + msg + "\r\n");
            }
            catch { }
        }

        #endregion

        #region ISwAddin 实现

        /// <summary>COM 激活即记录（证明 CoCreateInstance 到达了我们的 DLL）</summary>
        public SWAIAddin()
        {
            Log("SWAIAddin object CONSTRUCTED (COM activation reached our DLL)");
        }

        /// <summary>
        /// 连接插件。SolidWorks 装载插件时自动调用。
        /// </summary>
        /// <param name="ThisSW">SolidWorks 应用对象</param>
        /// <param name="Cookie">插件 ID</param>
        /// <returns>连接是否成功</returns>
        public bool ConnectToSW(object ThisSW, int Cookie)
        {
            try
            {
                Log("ConnectToSW ENTRY, cookie=" + Cookie + ", caller=" +
                    System.Diagnostics.Process.GetCurrentProcess().ProcessName);
                _swApp = (SldWorks)ThisSW;
                _addinId = Cookie;

                // SolidWorks 插件握手：注册回调后插件管理器才认本插件（缺此步对话框勾选会被弹回）
                _swApp.SetAddinCallbackInfo2(0, this, _addinId);
                Log("handshake SetAddinCallbackInfo2 OK");

                // 创建任务面板（核心 UI：AI 对话 + 手动模式）
                CreateTaskPane();

                _connected = true;
                Log("ConnectToSW SUCCESS");
                return true;
            }
            catch (Exception ex)
            {
                Log("ConnectToSW FAILED: " + ex);
                return false;
            }
        }

        /// <summary>
        /// 断开插件。SolidWorks 卸载插件时自动调用。
        /// </summary>
        /// <returns>断开是否成功</returns>
        public bool DisconnectFromSW()
        {
            try
            {
                RemoveTaskPane();

                _taskPane?.Dispose();
                _taskPane = null;
                _swApp = null;
                _connected = false;

                return true;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SWAI] Disconnect failed: " + ex.Message);
                return false;
            }
        }

        #endregion

        #region 任务面板管理

        // 16x16 任务窗格图标（橙底白字"SW"，BMP格式base64；橙色区别于蓝(WorkBuddy)/绿(Pro)两插件）
        private const string TaskPaneIconBase64 =
            "Qk02AwAAAAAAADYAAAAoAAAAEAAAABAAAAABABgAAAAAAAADAAATCwAAEwsAAAAAAAAAAAAACnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnbo////////////CnboCnboCnbo////CnboCnboCnbo////CnboCnboCnboCnbo////CnboCnboCnbo////CnboCnbo////////Cnbo////////CnboCnboCnboCnboCnboCnboCnboCnbo////CnboCnbo////Cnbo////Cnbo////CnboCnboCnboCnboCnboCnbo////////////CnboCnboCnbo////Cnbo////Cnbo////CnboCnboCnboCnbo////CnboCnboCnboCnboCnboCnbo////CnboCnboCnbo////CnboCnboCnbo////CnboCnboCnbo////CnboCnbo////CnboCnboCnbo////CnboCnboCnboCnboCnbo////////////CnboCnboCnbo////CnboCnboCnbo////CnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnboCnbo";

        /// <summary>
        /// 释放内置图标到ProgramData，返回文件路径（失败返回null）
        /// </summary>
        private static string EnsureIconFile()
        {
            try
            {
                string dir = @"C:\ProgramData\SWAIPlugin";
                if (!System.IO.Directory.Exists(dir))
                    System.IO.Directory.CreateDirectory(dir);
                string path = System.IO.Path.Combine(dir, "taskpane_icon.bmp");
                byte[] icon = Convert.FromBase64String(TaskPaneIconBase64);
                // 已存在且大小一致时跳过写入：SolidWorks可能占用该bmp导致覆写失败
                if (!System.IO.File.Exists(path) || new System.IO.FileInfo(path).Length != icon.Length)
                    System.IO.File.WriteAllBytes(path, icon);
                return path;
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// 创建任务面板（Task Pane）。
        /// 使用现代 API：CreateTaskpaneView2 + AddControl。
        /// </summary>
        private void CreateTaskPane()
        {
            try
            {
                _taskPane = new TaskPaneControl();

                // 任务窗格图标：无图标时按钮不可见，必须提供16x16位图
                string iconPath = EnsureIconFile();
                Log("CreateTaskPane: iconPath=" + (iconPath ?? "<null>"));
                _taskPaneView = _swApp.CreateTaskpaneView2(iconPath ?? "", "SWAI 参数化建模（法兰/风机）");
                Log("CreateTaskpaneView2 returned " + (_taskPaneView == null ? "NULL" : "view"));
                if (_taskPaneView == null)
                {
                    return;
                }

                // 将 UserControl 挂到任务窗格（需 TaskPaneControl 为 COM 可见）
                object control = _taskPaneView.AddControl(
                    "SWAI.TaskPaneControl",
                    "");
                Log("AddControl returned " + (control == null ? "NULL" : control.GetType().FullName));
                if (control == null)
                {
                    Log("AddControl failed");
                }
            }
            catch (Exception ex)
            {
                Log("CreateTaskPane EXCEPTION: " + ex);
            }
        }

        /// <summary>
        /// 移除任务面板。
        /// </summary>
        private void RemoveTaskPane()
        {
            try
            {
                if (_taskPaneView != null)
                {
                    _taskPaneView.DeleteView();
                    _taskPaneView = null;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SWAI] RemoveTaskPane failed: " + ex.Message);
            }
        }

        #endregion

        #region COM 注册/注销

        /// <summary>
        /// RegAsm 注册时调用。
        /// </summary>
        [ComRegisterFunction]
        public static void RegisterFunction(Type t)
        {
            // RegAsm 自动处理注册表项
        }

        /// <summary>
        /// RegAsm 注销时调用。
        /// </summary>
        [ComUnregisterFunction]
        public static void UnregisterFunction(Type t)
        {
            // RegAsm 自动处理注册表项
        }

        #endregion
    }
}
