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

        #region ISwAddin 实现

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
                _swApp = (SldWorks)ThisSW;
                _addinId = Cookie;

                // 创建任务面板（核心 UI：AI 对话 + 手动模式）
                CreateTaskPane();

                _connected = true;
                return true;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SWAI] Connect failed: " + ex.Message);
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

        /// <summary>
        /// 创建任务面板（Task Pane）。
        /// 使用现代 API：CreateTaskpaneView2 + AddControl。
        /// </summary>
        private void CreateTaskPane()
        {
            try
            {
                _taskPane = new TaskPaneControl();

                // 现代 API：创建任务窗格视图（空位图 + 提示）
                _taskPaneView = _swApp.CreateTaskpaneView2("", "SWAI 🏭");
                if (_taskPaneView == null)
                {
                    System.Diagnostics.Debug.WriteLine("[SWAI] CreateTaskpaneView2 returned null");
                    return;
                }

                // 将 UserControl 挂到任务窗格（需 TaskPaneControl 为 COM 可见）
                object control = _taskPaneView.AddControl(
                    "SWAI.TaskPaneControl",
                    "");
                if (control == null)
                {
                    System.Diagnostics.Debug.WriteLine("[SWAI] AddControl returned null");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("[SWAI] CreateTaskPane failed: " + ex.Message);
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
