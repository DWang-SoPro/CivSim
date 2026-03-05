use civsim::llm::client::LLMClient;

#[test]
fn test_llm_client_construction_qwen() {
    // Environment may not be set during unit tests; this test ensures construction succeeds.
    let client = LLMClient::new_qwen();
    // Basic sanity: model name should be non-empty
    assert!(!client.model_name().is_empty());
}

#[tokio::test]
async fn test_llm_client_chat_connection() {
    // Run only if API key is provided; otherwise ignore to avoid failing CI.
    if std::env::var("DASHSCOPE_API_KEY").is_err() {
        println!("DASHSCOPE_API_KEY not set; skipping integration test for llm chat");
        return;
    }
    // Build client and attempt a lightweight chat
    let client = LLMClient::new_qwen();
    let _ = client.chat("Hello civsim").await.expect("chat request failed");
}
