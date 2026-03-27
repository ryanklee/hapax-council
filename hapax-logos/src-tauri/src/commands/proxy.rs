//! Proxy commands that forward HTTP requests to the FastAPI logos API at :8051.
//!
//! These exist for endpoints that don't yet have native Rust implementations.
//! Each command is a thin IPC→HTTP bridge so the frontend never makes direct
//! HTTP calls — all traffic goes through Tauri invoke().

use serde_json::Value;

const LOGOS_BASE: &str = "http://127.0.0.1:8051/api";

// ── Reusable helpers ──────────────────────────────────────────────────────────

async fn proxy_get(path: &str) -> Result<Value, String> {
    let url = format!("{}{}", LOGOS_BASE, path);
    let resp = reqwest::get(&url)
        .await
        .map_err(|e| format!("proxy GET {}: {}", path, e))?;
    if !resp.status().is_success() {
        return Err(format!("proxy GET {} returned {}", path, resp.status()));
    }
    resp.json::<Value>()
        .await
        .map_err(|e| format!("proxy GET {} json: {}", path, e))
}

async fn proxy_post_json(path: &str, body: Option<Value>) -> Result<Value, String> {
    let url = format!("{}{}", LOGOS_BASE, path);
    let client = reqwest::Client::new();
    let req = if let Some(b) = body {
        client.post(&url).json(&b)
    } else {
        client.post(&url)
    };
    let resp = req
        .send()
        .await
        .map_err(|e| format!("proxy POST {}: {}", path, e))?;
    if !resp.status().is_success() {
        return Err(format!("proxy POST {} returned {}", path, resp.status()));
    }
    resp.json::<Value>()
        .await
        .map_err(|e| format!("proxy POST {} json: {}", path, e))
}

async fn proxy_delete_req(path: &str) -> Result<Value, String> {
    let url = format!("{}{}", LOGOS_BASE, path);
    let resp = reqwest::Client::new()
        .delete(&url)
        .send()
        .await
        .map_err(|e| format!("proxy DELETE {}: {}", path, e))?;
    if !resp.status().is_success() {
        return Err(format!("proxy DELETE {} returned {}", path, resp.status()));
    }
    resp.json::<Value>()
        .await
        .map_err(|e| format!("proxy DELETE {} json: {}", path, e))
}

// ── Generic proxy commands (for ChatProvider and other dynamic paths) ─────────

#[tauri::command]
pub async fn proxy_get_generic(path: String) -> Result<Value, String> {
    proxy_get(&path).await
}

#[tauri::command]
pub async fn proxy_post(path: String, body: Option<Value>) -> Result<Value, String> {
    proxy_post_json(&path, body).await
}

#[tauri::command]
pub async fn proxy_delete(path: String) -> Result<Value, String> {
    proxy_delete_req(&path).await
}

// ── Studio ────────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_compositor_live() -> Result<Value, String> {
    proxy_get("/studio/compositor/live").await
}

#[tauri::command]
pub async fn proxy_studio_disk() -> Result<Value, String> {
    proxy_get("/studio/disk").await
}

#[tauri::command]
pub async fn proxy_enable_recording() -> Result<Value, String> {
    proxy_post_json("/studio/recording/enable", None).await
}

#[tauri::command]
pub async fn proxy_disable_recording() -> Result<Value, String> {
    proxy_post_json("/studio/recording/disable", None).await
}

// ── Copilot ───────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_copilot() -> Result<Value, String> {
    proxy_get("/copilot").await
}

// ── Scout mutations ───────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_scout_decide(
    component: String,
    decision: String,
    notes: String,
) -> Result<Value, String> {
    let body = serde_json::json!({ "decision": decision, "notes": notes });
    proxy_post_json(
        &format!("/scout/{}/decide", component),
        Some(body),
    )
    .await
}

// ── Demo mutations ────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_delete_demo(id: String) -> Result<Value, String> {
    proxy_delete_req(&format!("/demos/{}", id)).await
}

// ── Governance & Consent ──────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_consent_contracts() -> Result<Value, String> {
    proxy_get("/consent/contracts").await
}

#[tauri::command]
pub async fn proxy_consent_trace(path: Option<String>) -> Result<Value, String> {
    match path {
        Some(p) => {
            let encoded = urlencoding::encode(&p);
            proxy_get(&format!("/consent/trace?path={}", encoded)).await
        }
        None => proxy_get("/consent/trace").await,
    }
}

#[tauri::command]
pub async fn proxy_consent_coverage() -> Result<Value, String> {
    proxy_get("/consent/coverage").await
}

#[tauri::command]
pub async fn proxy_consent_overhead() -> Result<Value, String> {
    proxy_get("/consent/overhead").await
}

#[tauri::command]
pub async fn proxy_consent_precedents() -> Result<Value, String> {
    proxy_get("/consent/precedents").await
}

#[tauri::command]
pub async fn proxy_governance_heartbeat() -> Result<Value, String> {
    proxy_get("/governance/heartbeat").await
}

#[tauri::command]
pub async fn proxy_governance_coverage() -> Result<Value, String> {
    proxy_get("/governance/coverage").await
}

#[tauri::command]
pub async fn proxy_governance_carriers() -> Result<Value, String> {
    proxy_get("/governance/carriers").await
}

// ── Engine ────────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_engine_status() -> Result<Value, String> {
    proxy_get("/engine/status").await
}

#[tauri::command]
pub async fn proxy_engine_rules() -> Result<Value, String> {
    proxy_get("/engine/rules").await
}

#[tauri::command]
pub async fn proxy_engine_history() -> Result<Value, String> {
    proxy_get("/engine/history").await
}

// ── Profile ───────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_profile() -> Result<Value, String> {
    proxy_get("/profile").await
}

#[tauri::command]
pub async fn proxy_profile_dimension(dim: String) -> Result<Value, String> {
    proxy_get(&format!("/profile/{}", dim)).await
}

#[tauri::command]
pub async fn proxy_profile_pending() -> Result<Value, String> {
    proxy_get("/profile/facts/pending").await
}

// ── Insight Queries ───────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_insight_queries() -> Result<Value, String> {
    proxy_get("/query/list").await
}

#[tauri::command]
pub async fn proxy_insight_query(id: String) -> Result<Value, String> {
    proxy_get(&format!("/query/{}", id)).await
}

#[tauri::command]
pub async fn proxy_run_insight_query(query: String) -> Result<Value, String> {
    proxy_post_json("/query/run", Some(serde_json::json!({ "query": query }))).await
}

#[tauri::command]
pub async fn proxy_refine_insight_query(
    query: String,
    parent_id: String,
    prior_result: String,
    agent_type: String,
) -> Result<Value, String> {
    proxy_post_json(
        "/query/refine",
        Some(serde_json::json!({
            "query": query,
            "parent_id": parent_id,
            "prior_result": prior_result,
            "agent_type": agent_type,
        })),
    )
    .await
}

#[tauri::command]
pub async fn proxy_delete_insight_query(id: String) -> Result<Value, String> {
    proxy_delete_req(&format!("/query/{}", id)).await
}

// ── Fortress ──────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn proxy_fortress_state() -> Result<Value, String> {
    proxy_get("/fortress/state").await
}

#[tauri::command]
pub async fn proxy_fortress_governance() -> Result<Value, String> {
    proxy_get("/fortress/governance").await
}

#[tauri::command]
pub async fn proxy_fortress_goals() -> Result<Value, String> {
    proxy_get("/fortress/goals").await
}

#[tauri::command]
pub async fn proxy_fortress_events() -> Result<Value, String> {
    proxy_get("/fortress/events").await
}

#[tauri::command]
pub async fn proxy_fortress_metrics() -> Result<Value, String> {
    proxy_get("/fortress/metrics").await
}

#[tauri::command]
pub async fn proxy_fortress_sessions() -> Result<Value, String> {
    proxy_get("/fortress/sessions").await
}

#[tauri::command]
pub async fn proxy_fortress_chronicle() -> Result<Value, String> {
    proxy_get("/fortress/chronicle").await
}
