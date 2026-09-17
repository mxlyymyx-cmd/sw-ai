using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace SWAI
{
    /// <summary>
    /// SWAI 任务面板控件。
    /// 
    /// 包含：
    /// - 顶部 Logo + 标题
    /// - AI 对话 Tab（多轮对话 → 自动建模）
    /// - 手动模式 Tab
    /// - 日志输出框
    /// - 底部状态栏
    /// </summary>
    [ComVisible(true)]
    [ProgId("SWAI.TaskPaneControl")]
    [Guid("A1B2C3D4-E5F6-7890-ABCD-EF1234567892")]
    public partial class TaskPaneControl : UserControl
    {
        #region 字段

        private readonly ApiClient _apiClient;
        private readonly List<Dictionary<string, string>> _chatHistory =
            new List<Dictionary<string, string>>();

        #endregion

        #region 构造函数

        /// <summary>
        /// 初始化 SWAI 任务面板。
        /// </summary>
        public TaskPaneControl()
        {
            InitializeComponent();
            _apiClient = new ApiClient("http://127.0.0.1:5757");

            // SolidWorks 任务窗格会拦截 Enter 键：标记为输入键确保送达控件，
            // 另加 KeyPress 兜底（KeyDown 在 SW COM 宿主中可能不触发）
            txtChatInput.PreviewKeyDown += (s, e) =>
            {
                if (e.KeyCode == Keys.Enter) { e.IsInputKey = true; }
            };
            txtChatInput.KeyPress += (s, e) =>
            {
                if (e.KeyChar == (char)Keys.Enter)
                {
                    e.Handled = true;
                    BtnChatSend_Click(s, e);
                }
            };

            // 默认选中 AI 对话
            tabControl1.SelectedIndex = 0;

            // 启动时检查后端健康状态
            _ = CheckBackendHealthAsync();

            // 欢迎消息
            AppendChat("🤖 我是 SWAI AI，直接告诉我你的设计需求，比如：\n" +
                       "\"设计一台离心风机 Q=5000 P=2500 n=1450\"\n" +
                       "\"DN100 PN16 平焊法兰\"", Color.FromArgb(144, 238, 144));
        }

        #endregion

        #region AI 对话

        /// <summary>
        /// 发送按钮点击。
        /// </summary>
        private async void BtnChatSend_Click(object sender, EventArgs e)
        {
            string userInput = txtChatInput.Text.Trim();
            if (string.IsNullOrEmpty(userInput))
            {
                AppendChat("⚠️ 请输入设计需求", Color.Orange);
                return;
            }

            // 清空输入框
            txtChatInput.Clear();

            // 显示用户消息
            AppendChat($"🧑 {userInput}", Color.FromArgb(135, 206, 250));

            // 加入历史
            _chatHistory.Add(new Dictionary<string, string>
            {
                { "role", "user" },
                { "content", userInput }
            });

            btnChatSend.Enabled = false;
            btnChatSend.Text = "⏳ 思考中…";

            try
            {
                // 调用 AI 聊天接口（携带完整历史，支持多轮追问）
                var chatResult = await _apiClient.ChatAsync(_chatHistory);
                if (!chatResult.IsSuccess)
                {
                    AppendChat($"❌ {chatResult.Error}", Color.Red);
                    AppendChat("   请确认后端已启动: python api.py --port 5757", Color.Gray);
                    return;
                }

                string reply = chatResult.GetValue("reply")?.ToString() ?? "";
                string action = chatResult.GetValue("action")?.ToString() ?? "chat";
                string macro = chatResult.GetValue("macro")?.ToString() ?? "";
                string extraMacro = chatResult.GetValue("extra_macro")?.ToString() ?? "";
                string extraName = chatResult.GetValue("extra_name")?.ToString() ?? "";
                bool llmUsed = false;
                try { llmUsed = Convert.ToBoolean(chatResult.GetValue("llm")); } catch { }

                // 显示 AI 回复
                AppendChat($"🤖 {reply}", llmUsed ? Color.FromArgb(144, 238, 144) : Color.LightGray);

                // AI 回复加入历史（多轮上下文）
                _chatHistory.Add(new Dictionary<string, string>
                {
                    { "role", "assistant" },
                    { "content", reply }
                });

                // 若为建模指令 → 自动在 SolidWorks 中建模
                if (action == "build" && !string.IsNullOrEmpty(macro))
                {
                    await Task.Delay(300);
                    bool built = await SwApiHelper.RunMacroAsync(macro);
                    AppendChat(built
                        ? "✅ 模型已自动生成！可在 SolidWorks 中查看。"
                        : "⚠️ 宏执行失败: " + SwApiHelper.LastMacroOutput,
                        built ? Color.FromArgb(144, 238, 144) : Color.Orange);

                    // 蜗壳宏（叶轮时附带）
                    if (!string.IsNullOrEmpty(extraMacro))
                    {
                        await Task.Delay(200);
                        bool builtVolute = await SwApiHelper.RunMacroAsync(extraMacro);
                        AppendChat(builtVolute
                            ? $"✅ 蜗壳模型已自动生成！"
                            : $"⚠️ 蜗壳宏执行失败 ({extraName}): " + SwApiHelper.LastMacroOutput,
                            builtVolute ? Color.FromArgb(144, 238, 144) : Color.Orange);
                    }
                }
            }
            catch (Exception ex)
            {
                AppendChat($"❌ 错误: {ex.Message}", Color.Red);
            }
            finally
            {
                btnChatSend.Enabled = true;
                btnChatSend.Text = "🚀 发送";
                txtChatInput.Focus();
            }
        }

        /// <summary>
        /// 输入框回车发送（Ctrl+Enter 换行）。
        /// </summary>
        private void TxtChatInput_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Enter && !e.Control && !e.Shift)
            {
                e.SuppressKeyPress = true;
                BtnChatSend_Click(sender, e);
            }
        }

        /// <summary>
        /// 清空对话。
        /// </summary>
        private void BtnChatClear_Click(object sender, EventArgs e)
        {
            _chatHistory.Clear();
            txtChatLog.Clear();
            AppendChat("🗑 对话已清空，开始新一轮设计吧！", Color.Gray);
        }

        /// <summary>
        /// 打开设置：配置 LLM API Key。
        /// </summary>
        private async void BtnChatSettings_Click(object sender, EventArgs e)
        {
            using (var dlg = new SettingsDialog())
            {
                // 预填当前配置
                try
                {
                    var cfg = await _apiClient.GetChatConfigAsync();
                    if (cfg.IsSuccess)
                    {
                        dlg.ApiUrl = cfg.GetValue("api_url")?.ToString() ?? "";
                        dlg.Model = cfg.GetValue("model")?.ToString() ?? "";
                    }
                }
                catch { }

                if (dlg.ShowDialog(this) == DialogResult.OK)
                {
                    SaveSettings(dlg.ApiKey, dlg.ApiUrl, dlg.Model);
                    AppendChat("⚙ 设置已保存！重新发送消息即可使用 AI 对话。", Color.Orange);
                }
            }
        }

        /// <summary>
        /// 保存设置到 %APPDATA%\SWAI\config.json。
        /// </summary>
        private static void SaveSettings(string apiKey, string apiUrl, string model)
        {
            try
            {
                string dir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    "SWAI");
                Directory.CreateDirectory(dir);

                string path = Path.Combine(dir, "config.json");
                var cfg = new System.Collections.Generic.Dictionary<string, string>
                {
                    { "llm_api_key", apiKey ?? "" },
                    { "llm_api_url", string.IsNullOrEmpty(apiUrl) ? "https://api.deepseek.com/v1/chat/completions" : apiUrl },
                    { "llm_model", string.IsNullOrEmpty(model) ? "deepseek-chat" : model }
                };
                string json = new System.Web.Script.Serialization.JavaScriptSerializer().Serialize(cfg);
                File.WriteAllText(path, json, System.Text.Encoding.UTF8);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"保存设置失败: {ex.Message}", "SWAI",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        #endregion

        #region 手动模式

        /// <summary>
        /// 「手动模式」生成按钮点击。
        /// </summary>
        private async void BtnManualGenerate_Click(object sender, EventArgs e)
        {
            string partType = cmbPartType.SelectedItem?.ToString() ?? "flange";
            btnManualGenerate.Enabled = false;

            try
            {
                object designParams = null;

                if (partType == "flange" || partType == "法兰")
                {
                    int dn = (int)numDn.Value;
                    int pn = (int)numPn.Value;
                    string flangeType = cmbFlangeType.SelectedItem?.ToString() ?? "plate";
                    string material = txtMaterial.Text.Trim();
                    if (string.IsNullOrEmpty(material)) material = "Q235B";

                    designParams = new
                    {
                        dn,
                        pn,
                        flange_type = flangeType,
                        material
                    };
                }
                else if (partType == "impeller" || partType == "离心风机")
                {
                    double Q = (double)numFanQ.Value;
                    double P = (double)numFanP.Value;
                    double n = (double)numFanN.Value;

                    designParams = new
                    {
                        Q,
                        P,
                        n,
                        blade_type = cmbBladeType.SelectedItem?.ToString() ?? "backward",
                        material = txtMaterial.Text.Trim() == "" ? "Q235B" : txtMaterial.Text.Trim()
                    };
                }
                else if (partType == "axial" || partType == "轴流风机")
                {
                    double Q = (double)numFanQ.Value;
                    double P = (double)numFanP.Value;
                    double n = (double)numFanN.Value;

                    designParams = new
                    {
                        Q,
                        P,
                        n,
                        airfoil = cmbAirfoil.SelectedItem?.ToString() ?? "clark_y",
                        material = txtMaterial.Text.Trim() == "" ? "Q235B" : txtMaterial.Text.Trim()
                    };
                }
                else
                {
                    AppendLog("⚠️ 未知零件类型", Color.Orange);
                    return;
                }

                AppendLog($"🔧 手动模式: {partType}", Color.Gray);

                // 设计计算
                var designResult = await _apiClient.DesignAsync(partType, designParams);
                if (!designResult.IsSuccess)
                {
                    AppendLog($"❌ 设计失败: {designResult.Error}", Color.Red);
                    return;
                }

                string summary = designResult.GetValue("summary")?.ToString() ?? "";
                if (!string.IsNullOrEmpty(summary))
                {
                    AppendLog($"📐 设计结果:\n{summary}", Color.Black);
                }

                // 生成 VBA 宏
                AppendLog($"📜 正在生成 VBA 宏...", Color.Blue);
                var macroResult = await _apiClient.GenerateMacroAsync(partType, designParams);
                if (macroResult.IsSuccess)
                {
                    string macroName = macroResult.GetValue("name")?.ToString() ?? "Unknown";
                    int lines = 0;
                    try { lines = Convert.ToInt32(macroResult.GetValue("lines")); } catch { }
                    AppendLog($"✅ VBA 宏生成: {macroName} ({lines} 行)", Color.Green);
                }
                else
                {
                    AppendLog($"⚠️ 宏生成失败: {macroResult.Error}", Color.Orange);
                }
            }
            catch (Exception ex)
            {
                AppendLog($"❌ 错误: {ex.Message}", Color.Red);
            }
            finally
            {
                btnManualGenerate.Enabled = true;
            }
        }

        /// <summary>
        /// 零件类型下拉选择变更。
        /// </summary>
        private void CmbPartType_SelectedIndexChanged(object sender, EventArgs e)
        {
            string selected = cmbPartType.SelectedItem?.ToString() ?? "";
            UpdateParameterPanel(selected);
        }

        #endregion

        #region AI 对话辅助

        /// <summary>
        /// 在聊天记录框追加消息，支持颜色。
        /// </summary>
        private void AppendChat(string text, Color color)
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() => AppendChat(text, color)));
                return;
            }

            txtChatLog.SelectionStart = txtChatLog.TextLength;
            txtChatLog.SelectionLength = 0;
            txtChatLog.SelectionColor = color;
            txtChatLog.AppendText(text + "\n\n");
            txtChatLog.ScrollToCaret();
        }

        #endregion

        #region 辅助方法

        /// <summary>
        /// 根据选择的零件类型更新参数面板显示。
        /// </summary>
        private void UpdateParameterPanel(string partType)
        {
            // 默认隐藏所有参数组
            pnlFlangeParams.Visible = false;
            pnlFanParams.Visible = false;
            pnlCommonParams.Visible = true;

            if (partType == "flange" || partType == "法兰")
            {
                pnlFlangeParams.Visible = true;
                pnlFanParams.Visible = false;
            }
            else if (partType == "impeller" || partType == "离心风机" ||
                     partType == "axial" || partType == "轴流风机")
            {
                pnlFlangeParams.Visible = false;
                pnlFanParams.Visible = true;
            }
            else
            {
                pnlCommonParams.Visible = true;
            }
        }

        /// <summary>
        /// 异步检查后端健康状况。
        /// </summary>
        private async Task CheckBackendHealthAsync()
        {
            try
            {
                var healthResult = await _apiClient.HealthCheckAsync();
                if (healthResult.IsSuccess)
                {
                    string version = healthResult.GetValue("version")?.ToString() ?? "?";
                    AppendLog($"✅ 后端连接成功 (v{version})", Color.Green);
                }
                else
                {
                    AppendLog("⚠️ 后端未响应，请确保 API 服务器已启动", Color.Orange);
                    AppendLog("   运行: python api.py --port 5757", Color.Gray);
                }
            }
            catch (Exception ex)
            {
                AppendLog("⚠️ 后端连接失败: " + ex.Message, Color.Orange);
                AppendLog("   运行: python api.py --port 5757", Color.Gray);
            }
        }

        /// <summary>
        /// 在日志框中追加文本，支持颜色。
        /// </summary>
        private void AppendLog(string text, Color color)
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() => AppendLog(text, color)));
                return;
            }

            txtLog.SelectionStart = txtLog.TextLength;
            txtLog.SelectionLength = 0;
            txtLog.SelectionColor = color;
            txtLog.AppendText($"[{DateTime.Now:HH:mm:ss}] {text}\n");
            txtLog.ScrollToCaret();
        }

        #endregion
    }
}
