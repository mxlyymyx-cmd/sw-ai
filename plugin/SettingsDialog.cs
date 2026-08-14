using System;
using System.Drawing;
using System.Windows.Forms;

namespace SWAI
{
    /// <summary>
    /// LLM 设置对话框 — 配置 API Key / URL / 模型。
    /// 保存位置: %APPDATA%\SWAI\config.json（后端自动读取）
    /// </summary>
    public class SettingsDialog : Form
    {
        private TextBox txtApiKey;
        private TextBox txtApiUrl;
        private TextBox txtModel;
        private Button btnOk;
        private Button btnCancel;

        /// <summary>API Key（只写）。</summary>
        public string ApiKey { get { return txtApiKey.Text.Trim(); } set { txtApiKey.Text = value; } }

        /// <summary>API URL（默认 DeepSeek）。</summary>
        public string ApiUrl { get { return txtApiUrl.Text.Trim(); } set { txtApiUrl.Text = value; } }

        /// <summary>模型名。</summary>
        public string Model { get { return txtModel.Text.Trim(); } set { txtModel.Text = value; } }

        public SettingsDialog()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text = "⚙ SWAI AI 设置";
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.StartPosition = FormStartPosition.CenterParent;
            this.ClientSize = new Size(380, 220);
            this.Font = new Font("Segoe UI", 9F);

            var lblKey = new Label { Text = "API Key:", Location = new Point(12, 15), Size = new Size(90, 20) };
            txtApiKey = new TextBox
            {
                Location = new Point(105, 12),
                Size = new Size(260, 23),
                UseSystemPasswordChar = true
            };

            var lblUrl = new Label { Text = "API URL:", Location = new Point(12, 50), Size = new Size(90, 20) };
            txtApiUrl = new TextBox
            {
                Location = new Point(105, 47),
                Size = new Size(260, 23),
                Text = "https://api.deepseek.com/v1/chat/completions"
            };

            var lblModel = new Label { Text = "模型:", Location = new Point(12, 85), Size = new Size(90, 20) };
            txtModel = new TextBox
            {
                Location = new Point(105, 82),
                Size = new Size(260, 23),
                Text = "deepseek-chat"
            };

            var hint = new Label
            {
                Text = "💡 支持任意 OpenAI 兼容接口：改 API URL + 模型即可\n   切换到 OpenAI / Qwen / 豆包 / Kimi 等。",
                Location = new Point(12, 118),
                Size = new Size(356, 40),
                ForeColor = Color.Gray
            };

            btnOk = new Button
            {
                Text = "✅ 保存",
                Location = new Point(200, 175),
                Size = new Size(80, 32),
                BackColor = Color.FromArgb(0, 120, 212),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            btnOk.Click += (s, e) => { DialogResult = DialogResult.OK; Close(); };

            btnCancel = new Button
            {
                Text = "取消",
                Location = new Point(286, 175),
                Size = new Size(80, 32),
                DialogResult = DialogResult.Cancel
            };

            this.Controls.Add(lblKey);
            this.Controls.Add(txtApiKey);
            this.Controls.Add(lblUrl);
            this.Controls.Add(txtApiUrl);
            this.Controls.Add(lblModel);
            this.Controls.Add(txtModel);
            this.Controls.Add(hint);
            this.Controls.Add(btnOk);
            this.Controls.Add(btnCancel);

            this.AcceptButton = btnOk;
            this.CancelButton = btnCancel;
        }
    }
}
