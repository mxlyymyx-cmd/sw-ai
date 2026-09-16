namespace SWAI
{
    partial class TaskPaneControl
    {
        private System.ComponentModel.IContainer components = null;

        // ── 顶部 ──
        private System.Windows.Forms.Label lblTitle;
        private System.Windows.Forms.Panel pnlHeader;

        // ── Tab ──
        private System.Windows.Forms.TabControl tabControl1;
        private System.Windows.Forms.TabPage tabAi;
        private System.Windows.Forms.TabPage tabManual;

        // ── AI 对话 ──
        private System.Windows.Forms.RichTextBox txtChatLog;
        private System.Windows.Forms.TextBox txtChatInput;
        private System.Windows.Forms.Button btnChatSend;
        private System.Windows.Forms.Button btnChatSettings;
        private System.Windows.Forms.Button btnChatClear;

        // ── 手动模式 ──
        private System.Windows.Forms.ComboBox cmbPartType;
        private System.Windows.Forms.Label lblPartType;

        // 法兰参数
        private System.Windows.Forms.Panel pnlFlangeParams;
        private System.Windows.Forms.NumericUpDown numDn;
        private System.Windows.Forms.NumericUpDown numPn;
        private System.Windows.Forms.ComboBox cmbFlangeType;
        private System.Windows.Forms.Label lblDn;
        private System.Windows.Forms.Label lblPn;
        private System.Windows.Forms.Label lblFlangeType;

        // 风机参数
        private System.Windows.Forms.Panel pnlFanParams;
        private System.Windows.Forms.NumericUpDown numFanQ;
        private System.Windows.Forms.NumericUpDown numFanP;
        private System.Windows.Forms.NumericUpDown numFanN;
        private System.Windows.Forms.ComboBox cmbBladeType;
        private System.Windows.Forms.ComboBox cmbAirfoil;
        private System.Windows.Forms.Label lblFanQ;
        private System.Windows.Forms.Label lblFanP;
        private System.Windows.Forms.Label lblFanN;
        private System.Windows.Forms.Label lblBladeType;
        private System.Windows.Forms.Label lblAirfoil;

        // 通用参数
        private System.Windows.Forms.Panel pnlCommonParams;
        private System.Windows.Forms.TextBox txtMaterial;

        private System.Windows.Forms.Button btnManualGenerate;

        // ── 底部 ──
        private System.Windows.Forms.RichTextBox txtLog;
        private System.Windows.Forms.StatusStrip statusStrip1;
        private System.Windows.Forms.ToolStripStatusLabel lblStatus;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Forms Designer generated code

        private void InitializeComponent()
        {
            this.lblTitle = new System.Windows.Forms.Label();
            this.pnlHeader = new System.Windows.Forms.Panel();
            this.tabControl1 = new System.Windows.Forms.TabControl();
            this.tabAi = new System.Windows.Forms.TabPage();
            this.tabManual = new System.Windows.Forms.TabPage();
            this.txtChatLog = new System.Windows.Forms.RichTextBox();
            this.txtChatInput = new System.Windows.Forms.TextBox();
            this.btnChatSend = new System.Windows.Forms.Button();
            this.btnChatSettings = new System.Windows.Forms.Button();
            this.btnChatClear = new System.Windows.Forms.Button();
            this.cmbPartType = new System.Windows.Forms.ComboBox();
            this.lblPartType = new System.Windows.Forms.Label();
            this.pnlFlangeParams = new System.Windows.Forms.Panel();
            this.numDn = new System.Windows.Forms.NumericUpDown();
            this.numPn = new System.Windows.Forms.NumericUpDown();
            this.cmbFlangeType = new System.Windows.Forms.ComboBox();
            this.lblDn = new System.Windows.Forms.Label();
            this.lblPn = new System.Windows.Forms.Label();
            this.lblFlangeType = new System.Windows.Forms.Label();
            this.pnlFanParams = new System.Windows.Forms.Panel();
            this.numFanQ = new System.Windows.Forms.NumericUpDown();
            this.numFanP = new System.Windows.Forms.NumericUpDown();
            this.numFanN = new System.Windows.Forms.NumericUpDown();
            this.cmbBladeType = new System.Windows.Forms.ComboBox();
            this.cmbAirfoil = new System.Windows.Forms.ComboBox();
            this.lblFanQ = new System.Windows.Forms.Label();
            this.lblFanP = new System.Windows.Forms.Label();
            this.lblFanN = new System.Windows.Forms.Label();
            this.lblBladeType = new System.Windows.Forms.Label();
            this.lblAirfoil = new System.Windows.Forms.Label();
            this.pnlCommonParams = new System.Windows.Forms.Panel();
            this.txtMaterial = new System.Windows.Forms.TextBox();
            this.btnManualGenerate = new System.Windows.Forms.Button();
            this.txtLog = new System.Windows.Forms.RichTextBox();
            this.statusStrip1 = new System.Windows.Forms.StatusStrip();
            this.lblStatus = new System.Windows.Forms.ToolStripStatusLabel();
            this.pnlHeader.SuspendLayout();
            this.tabControl1.SuspendLayout();
            this.tabAi.SuspendLayout();
            this.tabManual.SuspendLayout();
            this.pnlFlangeParams.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.numDn)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.numPn)).BeginInit();
            this.pnlFanParams.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.numFanQ)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.numFanP)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.numFanN)).BeginInit();
            this.pnlCommonParams.SuspendLayout();
            this.statusStrip1.SuspendLayout();
            this.SuspendLayout();

            // 
            // pnlHeader
            // 
            this.pnlHeader.BackColor = System.Drawing.Color.FromArgb(45, 45, 48);
            this.pnlHeader.Controls.Add(this.lblTitle);
            this.pnlHeader.Dock = System.Windows.Forms.DockStyle.Top;
            this.pnlHeader.Location = new System.Drawing.Point(0, 0);
            this.pnlHeader.Name = "pnlHeader";
            this.pnlHeader.Padding = new System.Windows.Forms.Padding(10, 8, 10, 8);
            this.pnlHeader.Size = new System.Drawing.Size(320, 52);
            this.pnlHeader.TabIndex = 0;

            // 
            // lblTitle
            // 
            this.lblTitle.AutoSize = true;
            this.lblTitle.Font = new System.Drawing.Font("Segoe UI", 16F, System.Drawing.FontStyle.Bold);
            this.lblTitle.ForeColor = System.Drawing.Color.White;
            this.lblTitle.Location = new System.Drawing.Point(10, 10);
            this.lblTitle.Name = "lblTitle";
            this.lblTitle.Size = new System.Drawing.Size(242, 30);
            this.lblTitle.Text = "SWAI 🏭";

            // 
            // tabControl1
            // 
            this.tabControl1.Controls.Add(this.tabAi);
            this.tabControl1.Controls.Add(this.tabManual);
            this.tabControl1.Dock = System.Windows.Forms.DockStyle.Top;
            this.tabControl1.Location = new System.Drawing.Point(0, 52);
            this.tabControl1.Name = "tabControl1";
            this.tabControl1.SelectedIndex = 0;
            this.tabControl1.Size = new System.Drawing.Size(320, 260);
            this.tabControl1.TabIndex = 1;

            // 
            // tabAi — AI 对话
            // 
            this.tabAi.Controls.Add(this.txtChatLog);
            this.tabAi.Controls.Add(this.txtChatInput);
            this.tabAi.Controls.Add(this.btnChatClear);
            this.tabAi.Controls.Add(this.btnChatSettings);
            this.tabAi.Controls.Add(this.btnChatSend);
            this.tabAi.Location = new System.Drawing.Point(4, 22);
            this.tabAi.Name = "tabAi";
            this.tabAi.Padding = new System.Windows.Forms.Padding(6);
            this.tabAi.Size = new System.Drawing.Size(312, 234);
            this.tabAi.Text = "AI 对话 💬";

            // txtChatLog — 聊天记录
            this.txtChatLog.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right;
            this.txtChatLog.BackColor = System.Drawing.Color.FromArgb(30, 30, 30);
            this.txtChatLog.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.txtChatLog.Font = new System.Drawing.Font("Microsoft YaHei", 9F);
            this.txtChatLog.ForeColor = System.Drawing.Color.LightGray;
            this.txtChatLog.Location = new System.Drawing.Point(6, 6);
            this.txtChatLog.Name = "txtChatLog";
            this.txtChatLog.ReadOnly = true;
            this.txtChatLog.ScrollBars = System.Windows.Forms.RichTextBoxScrollBars.Vertical;
            this.txtChatLog.Size = new System.Drawing.Size(296, 144);
            this.txtChatLog.TabIndex = 0;
            this.txtChatLog.Text = "";

            // txtChatInput — 输入框
            this.txtChatInput.AcceptsReturn = true;
            this.txtChatInput.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right;
            this.txtChatInput.Font = new System.Drawing.Font("Microsoft YaHei", 10F);
            this.txtChatInput.Location = new System.Drawing.Point(6, 156);
            this.txtChatInput.Multiline = true;
            this.txtChatInput.Name = "txtChatInput";
            this.txtChatInput.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.txtChatInput.Size = new System.Drawing.Size(296, 42);
            this.txtChatInput.TabIndex = 1;
            this.txtChatInput.Text = "设计一台离心风机 Q=5000 P=2500 n=1450";
            this.txtChatInput.KeyDown += new System.Windows.Forms.KeyEventHandler(this.TxtChatInput_KeyDown);

            // btnChatSend — 发送
            this.btnChatSend.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right;
            this.btnChatSend.BackColor = System.Drawing.Color.FromArgb(0, 120, 212);
            this.btnChatSend.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            this.btnChatSend.Font = new System.Drawing.Font("Segoe UI", 10F, System.Drawing.FontStyle.Bold);
            this.btnChatSend.ForeColor = System.Drawing.Color.White;
            this.btnChatSend.Location = new System.Drawing.Point(215, 204);
            this.btnChatSend.Name = "btnChatSend";
            this.btnChatSend.Size = new System.Drawing.Size(87, 26);
            this.btnChatSend.TabIndex = 2;
            this.btnChatSend.Text = "🚀 发送";
            this.btnChatSend.UseVisualStyleBackColor = false;
            this.btnChatSend.Click += new System.EventHandler(this.BtnChatSend_Click);

            // btnChatSettings — 设置
            this.btnChatSettings.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            this.btnChatSettings.Font = new System.Drawing.Font("Segoe UI", 9F);
            this.btnChatSettings.ForeColor = System.Drawing.Color.LightGray;
            this.btnChatSettings.Location = new System.Drawing.Point(6, 204);
            this.btnChatSettings.Name = "btnChatSettings";
            this.btnChatSettings.Size = new System.Drawing.Size(75, 26);
            this.btnChatSettings.TabIndex = 3;
            this.btnChatSettings.Text = "⚙ 设置";
            this.btnChatSettings.UseVisualStyleBackColor = true;
            this.btnChatSettings.Click += new System.EventHandler(this.BtnChatSettings_Click);

            // btnChatClear — 清空
            this.btnChatClear.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            this.btnChatClear.Font = new System.Drawing.Font("Segoe UI", 9F);
            this.btnChatClear.ForeColor = System.Drawing.Color.LightGray;
            this.btnChatClear.Location = new System.Drawing.Point(87, 204);
            this.btnChatClear.Name = "btnChatClear";
            this.btnChatClear.Size = new System.Drawing.Size(60, 26);
            this.btnChatClear.TabIndex = 4;
            this.btnChatClear.Text = "🗑 清空";
            this.btnChatClear.UseVisualStyleBackColor = true;
            this.btnChatClear.Click += new System.EventHandler(this.BtnChatClear_Click);

            // 
            // tabManual — 手动模式
            // 
            this.tabManual.AutoScroll = true;
            this.tabManual.Controls.Add(this.lblPartType);
            this.tabManual.Controls.Add(this.cmbPartType);
            this.tabManual.Controls.Add(this.pnlFlangeParams);
            this.tabManual.Controls.Add(this.pnlFanParams);
            this.tabManual.Controls.Add(this.pnlCommonParams);
            this.tabManual.Controls.Add(this.btnManualGenerate);
            this.tabManual.Location = new System.Drawing.Point(4, 22);
            this.tabManual.Name = "tabManual";
            this.tabManual.Padding = new System.Windows.Forms.Padding(10);
            this.tabManual.Size = new System.Drawing.Size(312, 234);
            this.tabManual.Text = "手动模式 🛠";

            // 
            // lblPartType / cmbPartType
            // 
            this.lblPartType.Location = new System.Drawing.Point(10, 10);
            this.lblPartType.Name = "lblPartType";
            this.lblPartType.Size = new System.Drawing.Size(60, 23);
            this.lblPartType.Text = "零件类型:";

            this.cmbPartType.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbPartType.Items.AddRange(new object[] {
                "flange",
                "impeller",
                "axial"
            });
            this.cmbPartType.Location = new System.Drawing.Point(80, 10);
            this.cmbPartType.Name = "cmbPartType";
            this.cmbPartType.Size = new System.Drawing.Size(110, 23);
            this.cmbPartType.SelectedIndex = 0;
            this.cmbPartType.SelectedIndexChanged += new System.EventHandler(this.CmbPartType_SelectedIndexChanged);

            // 
            // pnlFlangeParams
            // 
            this.pnlFlangeParams.Controls.Add(this.lblDn);
            this.pnlFlangeParams.Controls.Add(this.numDn);
            this.pnlFlangeParams.Controls.Add(this.lblPn);
            this.pnlFlangeParams.Controls.Add(this.numPn);
            this.pnlFlangeParams.Controls.Add(this.lblFlangeType);
            this.pnlFlangeParams.Controls.Add(this.cmbFlangeType);
            this.pnlFlangeParams.Location = new System.Drawing.Point(10, 40);
            this.pnlFlangeParams.Name = "pnlFlangeParams";
            this.pnlFlangeParams.Size = new System.Drawing.Size(290, 100);
            this.pnlFlangeParams.Visible = true;

            this.lblDn.Location = new System.Drawing.Point(5, 5);
            this.lblDn.Name = "lblDn";
            this.lblDn.Size = new System.Drawing.Size(40, 23);
            this.lblDn.Text = "DN:";

            this.numDn.Location = new System.Drawing.Point(50, 5);
            this.numDn.Maximum = 2000;
            this.numDn.Minimum = 10;
            this.numDn.Name = "numDn";
            this.numDn.Size = new System.Drawing.Size(80, 23);
            this.numDn.Value = 100;

            this.lblPn.Location = new System.Drawing.Point(140, 5);
            this.lblPn.Name = "lblPn";
            this.lblPn.Size = new System.Drawing.Size(40, 23);
            this.lblPn.Text = "PN:";

            this.numPn.Location = new System.Drawing.Point(180, 5);
            this.numPn.Maximum = 400;
            this.numPn.Minimum = 6;
            this.numPn.Name = "numPn";
            this.numPn.Size = new System.Drawing.Size(80, 23);
            this.numPn.Value = 16;

            this.lblFlangeType.Location = new System.Drawing.Point(5, 35);
            this.lblFlangeType.Name = "lblFlangeType";
            this.lblFlangeType.Size = new System.Drawing.Size(50, 23);
            this.lblFlangeType.Text = "类型:";

            this.cmbFlangeType.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbFlangeType.Items.AddRange(new object[] { "plate", "slip_on", "weld_neck", "blind" });
            this.cmbFlangeType.Location = new System.Drawing.Point(60, 35);
            this.cmbFlangeType.Name = "cmbFlangeType";
            this.cmbFlangeType.Size = new System.Drawing.Size(100, 23);
            this.cmbFlangeType.SelectedIndex = 0;

            // 
            // pnlFanParams
            // 
            this.pnlFanParams.Controls.Add(this.lblFanQ);
            this.pnlFanParams.Controls.Add(this.numFanQ);
            this.pnlFanParams.Controls.Add(this.lblFanP);
            this.pnlFanParams.Controls.Add(this.numFanP);
            this.pnlFanParams.Controls.Add(this.lblFanN);
            this.pnlFanParams.Controls.Add(this.numFanN);
            this.pnlFanParams.Controls.Add(this.lblBladeType);
            this.pnlFanParams.Controls.Add(this.cmbBladeType);
            this.pnlFanParams.Controls.Add(this.lblAirfoil);
            this.pnlFanParams.Controls.Add(this.cmbAirfoil);
            this.pnlFanParams.Location = new System.Drawing.Point(10, 40);
            this.pnlFanParams.Name = "pnlFanParams";
            this.pnlFanParams.Size = new System.Drawing.Size(290, 130);
            this.pnlFanParams.Visible = false;

            this.lblFanQ.Location = new System.Drawing.Point(5, 5);
            this.lblFanQ.Name = "lblFanQ";
            this.lblFanQ.Size = new System.Drawing.Size(40, 23);
            this.lblFanQ.Text = "Q (m³/h):";

            this.numFanQ.Location = new System.Drawing.Point(85, 5);
            this.numFanQ.Maximum = 999999;
            this.numFanQ.Minimum = 1;
            this.numFanQ.Name = "numFanQ";
            this.numFanQ.Size = new System.Drawing.Size(100, 23);
            this.numFanQ.Value = 5000;

            this.lblFanP.Location = new System.Drawing.Point(5, 35);
            this.lblFanP.Name = "lblFanP";
            this.lblFanP.Size = new System.Drawing.Size(60, 23);
            this.lblFanP.Text = "P (Pa):";

            this.numFanP.Location = new System.Drawing.Point(85, 35);
            this.numFanP.Maximum = 99999;
            this.numFanP.Minimum = 1;
            this.numFanP.Name = "numFanP";
            this.numFanP.Size = new System.Drawing.Size(100, 23);
            this.numFanP.Value = 2500;

            this.lblFanN.Location = new System.Drawing.Point(5, 65);
            this.lblFanN.Name = "lblFanN";
            this.lblFanN.Size = new System.Drawing.Size(60, 23);
            this.lblFanN.Text = "n (r/min):";

            this.numFanN.Location = new System.Drawing.Point(85, 65);
            this.numFanN.Maximum = 99999;
            this.numFanN.Minimum = 1;
            this.numFanN.Name = "numFanN";
            this.numFanN.Size = new System.Drawing.Size(100, 23);
            this.numFanN.Value = 1450;

            this.lblBladeType.Location = new System.Drawing.Point(5, 95);
            this.lblBladeType.Name = "lblBladeType";
            this.lblBladeType.Size = new System.Drawing.Size(60, 23);
            this.lblBladeType.Text = "叶型:";

            this.cmbBladeType.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbBladeType.Items.AddRange(new object[] { "backward", "forward", "radial", "airfoil" });
            this.cmbBladeType.Location = new System.Drawing.Point(70, 95);
            this.cmbBladeType.Name = "cmbBladeType";
            this.cmbBladeType.Size = new System.Drawing.Size(100, 23);
            this.cmbBladeType.SelectedIndex = 0;

            this.lblAirfoil.Location = new System.Drawing.Point(180, 95);
            this.lblAirfoil.Name = "lblAirfoil";
            this.lblAirfoil.Size = new System.Drawing.Size(40, 23);
            this.lblAirfoil.Text = "翼型:";

            this.cmbAirfoil.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbAirfoil.Items.AddRange(new object[] { "clark_y", "naca_4412", "raf_30" });
            this.cmbAirfoil.Location = new System.Drawing.Point(220, 95);
            this.cmbAirfoil.Name = "cmbAirfoil";
            this.cmbAirfoil.Size = new System.Drawing.Size(60, 23);
            this.cmbAirfoil.SelectedIndex = 0;

            // 
            // pnlCommonParams
            // 
            this.pnlCommonParams.Controls.Add(this.txtMaterial);
            this.pnlCommonParams.Location = new System.Drawing.Point(10, 170);
            this.pnlCommonParams.Name = "pnlCommonParams";
            this.pnlCommonParams.Size = new System.Drawing.Size(290, 30);
            this.pnlCommonParams.Visible = true;

            // txtMaterial — 材料
            this.txtMaterial.Location = new System.Drawing.Point(5, 5);
            this.txtMaterial.Name = "txtMaterial";
            this.txtMaterial.Size = new System.Drawing.Size(140, 23);
            this.txtMaterial.Text = "Q235B";

            // 
            // btnManualGenerate
            // 
            this.btnManualGenerate.BackColor = System.Drawing.Color.FromArgb(0, 120, 212);
            this.btnManualGenerate.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            this.btnManualGenerate.Font = new System.Drawing.Font("Segoe UI", 10F, System.Drawing.FontStyle.Bold);
            this.btnManualGenerate.ForeColor = System.Drawing.Color.White;
            this.btnManualGenerate.Location = new System.Drawing.Point(180, 200);
            this.btnManualGenerate.Name = "btnManualGenerate";
            this.btnManualGenerate.Size = new System.Drawing.Size(110, 30);
            this.btnManualGenerate.TabIndex = 10;
            this.btnManualGenerate.Text = "⚡  生成";
            this.btnManualGenerate.UseVisualStyleBackColor = false;
            this.btnManualGenerate.Click += new System.EventHandler(this.BtnManualGenerate_Click);

            // 
            // txtLog — 日志输出框
            // 
            this.txtLog.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right;
            this.txtLog.BackColor = System.Drawing.Color.FromArgb(30, 30, 30);
            this.txtLog.Font = new System.Drawing.Font("Consolas", 9F);
            this.txtLog.ForeColor = System.Drawing.Color.LightGray;
            this.txtLog.Location = new System.Drawing.Point(0, 312);
            this.txtLog.Name = "txtLog";
            this.txtLog.ReadOnly = true;
            this.txtLog.Size = new System.Drawing.Size(320, 160);
            this.txtLog.TabIndex = 2;
            this.txtLog.Text = "";
            this.txtLog.WordWrap = true;

            // 
            // statusStrip1
            // 
            this.statusStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
                this.lblStatus
            });
            this.statusStrip1.Location = new System.Drawing.Point(0, 472);
            this.statusStrip1.Name = "statusStrip1";
            this.statusStrip1.Size = new System.Drawing.Size(320, 22);
            this.statusStrip1.TabIndex = 3;

            this.lblStatus.ForeColor = System.Drawing.Color.Gray;
            this.lblStatus.Text = "已就绪";

            // 
            // TaskPaneControl
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(96F, 96F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Dpi;
            this.AutoScroll = true;
            this.BackColor = System.Drawing.Color.FromArgb(37, 37, 38);
            this.Controls.Add(this.txtLog);
            this.Controls.Add(this.tabControl1);
            this.Controls.Add(this.pnlHeader);
            this.Controls.Add(this.statusStrip1);
            this.Font = new System.Drawing.Font("Segoe UI", 9F);
            this.MinimumSize = new System.Drawing.Size(320, 494);
            this.Name = "TaskPaneControl";
            this.Size = new System.Drawing.Size(320, 494);
            this.pnlHeader.ResumeLayout(false);
            this.pnlHeader.PerformLayout();
            this.tabControl1.ResumeLayout(false);
            this.tabAi.ResumeLayout(false);
            this.tabAi.PerformLayout();
            this.tabManual.ResumeLayout(false);
            this.tabManual.PerformLayout();
            this.pnlFlangeParams.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)(this.numDn)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.numPn)).EndInit();
            this.pnlFanParams.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)(this.numFanQ)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.numFanP)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.numFanN)).EndInit();
            this.pnlCommonParams.ResumeLayout(false);
            this.pnlCommonParams.PerformLayout();
            this.statusStrip1.ResumeLayout(false);
            this.statusStrip1.PerformLayout();
            this.ResumeLayout(false);
            this.PerformLayout();
        }

        #endregion
    }
}
