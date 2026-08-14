using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace SWAI
{
    /// <summary>
    /// API 调用结果封装。
    /// </summary>
    public class ApiResult
    {
        /// <summary>是否成功。</summary>
        public bool IsSuccess { get; set; }

        /// <summary>响应数据（JSON 对象）。</summary>
        public dynamic Data { get; set; }

        /// <summary>错误消息。</summary>
        public string Error { get; set; }

        /// <summary>HTTP 状态码。</summary>
        public int StatusCode { get; set; }

        public static ApiResult Success(dynamic data, int statusCode = 200)
        {
            return new ApiResult { IsSuccess = true, Data = data, StatusCode = statusCode };
        }

        public static ApiResult Failure(string error, int statusCode = 400)
        {
            return new ApiResult { IsSuccess = false, Error = error, StatusCode = statusCode };
        }
    }

    /// <summary>
    /// SWAI API HTTP 客户端。
    /// 
    /// 通过 HTTP POST/GET 与本地 Python API 服务器 (localhost:5757) 通信。
    /// 所有调用超时 60 秒，异步。
    /// </summary>
    public class ApiClient : IDisposable
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private readonly JavaScriptSerializer _jsonSerializer;

        /// <summary>
        /// 创建 API 客户端。
        /// </summary>
        /// <param name="baseUrl">API 基础 URL，如 "http://127.0.0.1:5757"</param>
        public ApiClient(string baseUrl)
        {
            _baseUrl = baseUrl.TrimEnd('/');
            _httpClient = new HttpClient();
            _httpClient.Timeout = TimeSpan.FromSeconds(60);
            _jsonSerializer = new JavaScriptSerializer();
        }

        /// <summary>
        /// 释放 HttpClient 资源。
        /// </summary>
        public void Dispose()
        {
            _httpClient?.Dispose();
        }

        #region API 方法

        /// <summary>
        /// AI 多轮对话 — POST /api/chat
        /// </summary>
        /// <param name="messages">对话历史 [{"role":"user|assistant","content":"..."}]</param>
        public async Task<ApiResult> ChatAsync(object messages)
        {
            return await PostAsync("/api/chat", new { messages });
        }

        /// <summary>
        /// 查询 LLM 配置状态 — GET /api/chat/config
        /// </summary>
        public async Task<ApiResult> GetChatConfigAsync()
        {
            return await GetAsync("/api/chat/config");
        }

        /// <summary>
        /// 健康检查 — GET /api/health
        /// </summary>
        public async Task<ApiResult> HealthCheckAsync()
        {
            return await GetAsync("/api/health");
        }

        /// <summary>
        /// 自然语言解析 — POST /api/nlp
        /// </summary>
        /// <param name="text">用户输入的自然语言</param>
        public async Task<ApiResult> NlpParseAsync(string text)
        {
            return await PostAsync("/api/nlp", new { text });
        }

        /// <summary>
        /// 设计计算 — POST /api/design/{type}
        /// </summary>
        /// <param name="partType">零件类型 (flange/impeller/axial)</param>
        /// <param name="designParams">设计参数对象</param>
        public async Task<ApiResult> DesignAsync(string partType, object designParams)
        {
            string endpoint = partType switch
            {
                "flange" => "/api/design/flange",
                "impeller" => "/api/design/impeller",
                "axial" => "/api/design/axial",
                _ => throw new ArgumentException($"Unknown part type: {partType}")
            };
            return await PostAsync(endpoint, designParams);
        }

        /// <summary>
        /// 生成 VBA 宏代码 — POST /api/macro
        /// </summary>
        /// <param name="partType">零件类型</param>
        /// <param name="designParams">设计参数</param>
        public async Task<ApiResult> GenerateMacroAsync(string partType, object designParams)
        {
            return await PostAsync("/api/macro", new
            {
                type = partType,
                @params = designParams
            });
        }

        /// <summary>
        /// 查看已生成的宏 — GET /api/macro/{taskId}
        /// </summary>
        /// <param name="taskId">任务 ID</param>
        public async Task<ApiResult> GetMacroAsync(string taskId)
        {
            return await GetAsync($"/api/macro/{taskId}");
        }

        #endregion

        #region HTTP 基础方法

        /// <summary>
        /// 发送 GET 请求。
        /// </summary>
        private async Task<ApiResult> GetAsync(string path)
        {
            try
            {
                string url = _baseUrl + path;
                var response = await _httpClient.GetAsync(url);
                string body = await response.Content.ReadAsStringAsync();
                return ParseResponse(response, body);
            }
            catch (TaskCanceledException)
            {
                return ApiResult.Failure("请求超时 (60s)", 408);
            }
            catch (HttpRequestException ex)
            {
                return ApiResult.Failure("网络错误: " + ex.Message, 503);
            }
            catch (Exception ex)
            {
                return ApiResult.Failure("未知错误: " + ex.Message, 500);
            }
        }

        /// <summary>
        /// 发送 POST 请求。
        /// </summary>
        private async Task<ApiResult> PostAsync(string path, object payload)
        {
            try
            {
                string url = _baseUrl + path;
                string jsonPayload = _jsonSerializer.Serialize(payload);
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync(url, content);
                string body = await response.Content.ReadAsStringAsync();
                return ParseResponse(response, body);
            }
            catch (TaskCanceledException)
            {
                return ApiResult.Failure("请求超时 (60s)", 408);
            }
            catch (HttpRequestException ex)
            {
                return ApiResult.Failure("网络错误: " + ex.Message, 503);
            }
            catch (Exception ex)
            {
                return ApiResult.Failure("未知错误: " + ex.Message, 500);
            }
        }

        /// <summary>
        /// 解析 API 响应 JSON。
        /// </summary>
        private ApiResult ParseResponse(HttpResponseMessage response, string body)
        {
            int statusCode = (int)response.StatusCode;

            try
            {
                dynamic json = _jsonSerializer.DeserializeObject(body);
                if (json is System.Collections.Generic.Dictionary<string, object> dict)
                {
                    // Python API 返回格式: {"success": true/false, "data": {...}, "error": "..."}
                    if (dict.TryGetValue("success", out object successObj) &&
                        Convert.ToBoolean(successObj) &&
                        dict.TryGetValue("data", out object dataObj))
                    {
                        return ApiResult.Success(dataObj, statusCode);
                    }

                    // 失败
                    string errorMsg = dict.TryGetValue("error", out object errObj)
                        ? errObj?.ToString() ?? "未知错误"
                        : "未知错误";
                    return ApiResult.Failure(errorMsg, statusCode);
                }

                return ApiResult.Success(json, statusCode);
            }
            catch (Exception ex)
            {
                return ApiResult.Failure($"JSON 解析失败: {ex.Message}", statusCode);
            }
        }

        #endregion
    }
}
