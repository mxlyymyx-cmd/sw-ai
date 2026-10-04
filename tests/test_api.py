"""API 层测试：Flask test client 全端点离线测试。

不启动真实服务、不触 SolidWorks COM、LLM 强制关闭（conftest autouse 夹具
清掉全部 key 来源），/api/chat 与 /api/nlp 走正则降级模式，结果确定性。
"""

import pytest

from app.api import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── 基础端点 ──────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"
    assert set(data["data"]["engines"]) == {"flange", "impeller", "axial", "select", "curve"}


def test_models_lists_four_types(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    models = r.get_json()["data"]["models"]
    assert {m["id"] for m in models} == {"flange", "impeller", "axial", "select"}
    for m in models:
        assert m["params"], f"{m['id']} 缺少参数说明"


def test_chat_config_reports_unconfigured(client):
    r = client.get("/api/chat/config")
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["configured"] is False  # conftest 已隔离全部 key 来源


def test_unknown_route_404(client):
    assert client.get("/api/nope").status_code == 404


# ── CORS：仅本机来源放行 ──────────────────────────────────

def test_cors_blocks_foreign_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://evil.example.com"})
    assert r.headers.get("Access-Control-Allow-Origin") is None


def test_cors_allows_local_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:3000"


def test_cors_allows_localhost(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"


# ── /api/chat（正则模式对话 → 设计 → 宏）─────────────────

def _chat(client, text):
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": text}]})
    assert r.status_code == 200
    return r.get_json()["data"]


def test_chat_design_flange(client):
    d = _chat(client, "DN100 PN16 带颈平焊法兰")
    assert d["action"] == "build"
    assert d["type"] == "flange"
    assert d["name"].startswith("Flange_DN100_PN16_")
    assert d["macro"]  # 生成了宏文本
    assert d["llm"] is False  # 离线正则模式


def test_chat_flange_missing_params_asks(client):
    d = _chat(client, "帮我设计一个法兰")
    assert d["action"] == "ask"
    assert "DN" in d["reply"] and "PN" in d["reply"]


def test_chat_smalltalk(client):
    d = _chat(client, "你好呀")
    assert d["action"] == "chat"
    assert d["macro"] == ""


def test_chat_design_impeller_with_volute(client):
    d = _chat(client, "设计一台离心风机 Q=5000 P=2500 n=1450")
    assert d["action"] == "build"
    assert d["type"] == "impeller"
    assert d["extra_macro"]  # 默认附带蜗壳宏
    assert d["extra_name"].endswith("_volute")


def test_chat_impeller_auto_speed(client):
    d = _chat(client, "设计一台离心风机 Q=5000 P=2500")
    assert d["action"] == "build"
    assert "自动选型" in d["summary"]


def test_chat_select_picks_machine(client):
    d = _chat(client, "帮我选型 Q=20000 P=800")
    assert d["action"] == "build"
    assert d["type"] in {"impeller", "axial"}
    assert d["macro"]


def test_chat_unsupported_dn_reports_failure(client):
    d = _chat(client, "DN999 PN16 法兰")
    assert d["action"] == "ask"
    assert "设计失败" in d["reply"]


def test_chat_empty_messages_400(client):
    r = client.post("/api/chat", json={"messages": []})
    assert r.status_code == 400
    assert r.get_json()["code"] == "EMPTY_INPUT"


# ── /api/nlp（自然语言 → 结构化参数）─────────────────────

def test_nlp_flange(client):
    r = client.post("/api/nlp", json={"text": "DN100 PN16 平焊法兰"})
    data = r.get_json()["data"]
    assert data["type"] == "flange"
    assert data["params"]["dn"] == 100
    assert data["params"]["pn"] == 16


def test_nlp_impeller(client):
    r = client.post("/api/nlp", json={"text": "离心风机 Q=5000 P=2500 n=1450 后向"})
    data = r.get_json()["data"]
    assert data["type"] == "impeller"
    assert data["params"]["Q"] == 5000.0
    assert data["params"]["blade_type"] == "backward"


def test_nlp_axial_with_airfoil(client):
    r = client.post("/api/nlp", json={"text": "轴流风机 Q=20000 P=800 clark_y"})
    data = r.get_json()["data"]
    assert data["type"] == "axial"
    assert data["params"]["airfoil"] == "clark_y"


def test_nlp_empty_text_400(client):
    r = client.post("/api/nlp", json={"text": "  "})
    assert r.status_code == 400
    assert r.get_json()["code"] == "EMPTY_INPUT"


# ── /api/design/*（设计计算）──────────────────────────────

def test_design_flange_ok(client):
    r = client.post("/api/design/flange", json={"dn": 100, "pn": 16, "flange_type": "weld_neck"})
    data = r.get_json()["data"]
    assert data["standard"]
    assert data["params"]["flange_type"] == "weld_neck"
    assert data["bolt_hole_pattern"]
    assert data["summary"]


def test_design_flange_overrides(client):
    r = client.post("/api/design/flange", json={"dn": 100, "pn": 16, "material": "304", "n": 12})
    data = r.get_json()["data"]
    assert data["params"]["material"] == "304"
    assert data["params"]["n"] == 12


def test_design_flange_invalid_params_400(client):
    r = client.post("/api/design/flange", json={"dn": 0, "pn": 16})
    assert r.status_code == 400
    assert r.get_json()["code"] == "INVALID_PARAMS"


def test_design_flange_unsupported_400(client):
    r = client.post("/api/design/flange", json={"dn": 999, "pn": 16})
    assert r.status_code == 400
    assert r.get_json()["code"] == "NOT_SUPPORTED"


def test_design_impeller_ok_with_volute(client):
    r = client.post("/api/design/impeller", json={"Q": 5000, "P": 2500, "n": 1450})
    data = r.get_json()["data"]
    assert data["design"]["D2"] > 0
    assert data["volute"] is not None
    assert len(data["volute"]["profile_points"]) <= 10  # 只返回前 10 个点示意
    assert data["auto_speed"] is False


def test_design_impeller_without_volute(client):
    r = client.post("/api/design/impeller", json={"Q": 5000, "P": 2500, "n": 1450, "volute": False})
    assert r.get_json()["data"]["volute"] is None


def test_design_impeller_auto_speed(client):
    r = client.post("/api/design/impeller", json={"Q": 5000, "P": 2500})
    data = r.get_json()["data"]
    assert data["auto_speed"] is True
    assert data["design"]["D2"] > 0


def test_design_impeller_nonpositive_400(client):
    r = client.post("/api/design/impeller", json={"Q": -1, "P": 2500})
    assert r.status_code == 400
    assert r.get_json()["code"] == "INVALID_PARAMS"


def test_design_axial_ok(client):
    r = client.post("/api/design/axial", json={"Q": 20000, "P": 800, "n": 1450})
    data = r.get_json()["data"]
    assert len(data["sections"]) == 5
    assert data["design"]["D"] > 0


def test_design_axial_auto_speed(client):
    r = client.post("/api/design/axial", json={"Q": 30000, "P": 400})
    data = r.get_json()["data"]
    assert data["auto_speed"] is True
    assert len(data["sections"]) == 5


def test_design_axial_nonpositive_400(client):
    r = client.post("/api/design/axial", json={"Q": 0, "P": 800})
    assert r.status_code == 400


def test_design_select_best_and_candidates(client):
    r = client.post("/api/design/select", json={"Q": 20000, "P": 800})
    data = r.get_json()["data"]
    assert data["best"]["machine"] in {"centrifugal", "axial"}
    assert len(data["candidates"]) >= 1
    assert data["summary"]


def test_design_select_prefer_centrifugal(client):
    r = client.post("/api/design/select", json={"Q": 5000, "P": 2500, "prefer": "centrifugal"})
    assert r.get_json()["data"]["best"]["machine"] == "centrifugal"


def test_design_select_nonpositive_400(client):
    r = client.post("/api/design/select", json={"Q": 0, "P": 0})
    assert r.status_code == 400


def test_design_curve_impeller(client):
    r = client.post("/api/design/curve", json={"type": "impeller", "Q": 5000, "P": 2500, "n": 1450})
    data = r.get_json()["data"]
    assert data["machine"] == "centrifugal"  # perf 层对离心机的机型标签
    assert data["points"]
    assert {"Q", "P", "eta", "N"} <= set(data["points"][0])


def test_design_curve_axial_auto_speed(client):
    r = client.post("/api/design/curve", json={"type": "axial", "Q": 30000, "P": 400})
    data = r.get_json()["data"]
    assert data["machine"] == "axial"
    assert data["n"] > 0


def test_design_curve_bad_type_400(client):
    r = client.post("/api/design/curve", json={"type": "flange", "Q": 1, "P": 1})
    assert r.status_code == 400


# ── /api/macro（宏生成 + 任务存取）────────────────────────

def test_macro_flange(client):
    r = client.post("/api/macro", json={"type": "flange", "params": {"dn": 100, "pn": 16}})
    data = r.get_json()["data"]
    assert data["name"] == "Flange_DN100_PN16_plate"
    assert data["lines"] > 0
    assert data["macro"]


def test_macro_impeller_includes_volute_task(client):
    r = client.post("/api/macro", json={"type": "impeller",
                                        "params": {"Q": 5000, "P": 2500, "n": 1450}})
    data = r.get_json()["data"]
    assert data["volute_task_id"]
    assert data["volute_lines"] > 0


def test_macro_impeller_auto_speed(client):
    r = client.post("/api/macro", json={"type": "impeller", "params": {"Q": 5000, "P": 2500}})
    assert r.get_json()["data"]["name"].startswith("Impeller_Q5000_P2500_n")


def test_macro_axial(client):
    r = client.post("/api/macro", json={"type": "axial",
                                        "params": {"Q": 20000, "P": 800, "n": 1450}})
    assert r.get_json()["data"]["name"].startswith("Axial_Q20000_P800_n1450")


def test_macro_unsupported_type_400(client):
    r = client.post("/api/macro", json={"type": "bearing", "params": {}})
    assert r.status_code == 400
    assert r.get_json()["code"] == "UNSUPPORTED_TYPE"


def test_macro_flange_missing_params_400(client):
    r = client.post("/api/macro", json={"type": "flange", "params": {"dn": 100}})
    assert r.status_code == 400
    assert r.get_json()["code"] == "INVALID_PARAMS"


def test_macro_fetch_roundtrip(client):
    created = client.post("/api/macro",
                          json={"type": "flange", "params": {"dn": 50, "pn": 10}}).get_json()["data"]
    r = client.get(f"/api/macro/{created['task_id']}")
    assert r.status_code == 200
    fetched = r.get_json()["data"]
    assert fetched["macro"] == created["macro"]


def test_macro_fetch_unknown_404(client):
    r = client.get("/api/macro/999999")
    assert r.status_code == 404
    assert r.get_json()["code"] == "NOT_FOUND"
