from app.services.browser_policy_service import BrowserPolicyError, BrowserPolicyService


def test_approved_origin_persists_without_requests_or_sensitive_data(tmp_path):
    policy_path = tmp_path / "browser_origin_policy.json"
    service = BrowserPolicyService(policy_path)

    request = service.request_origin(origin="https://erp.example.com", purpose="business")
    service.decide_origin_request(request_id=request["id"], approved=True)

    reloaded = BrowserPolicyService(policy_path)
    assert reloaded.list_origins()[0]["origin"] == "https://erp.example.com"
    assert reloaded.purpose_for("https://erp.example.com") == "business"
    assert "request" not in policy_path.read_text(encoding="utf-8")


def test_origin_must_be_exact_https_and_approval_is_single_use(tmp_path):
    service = BrowserPolicyService(tmp_path / "policy.json")

    for invalid in ("http://erp.example.com", "https://*.example.com", "https://erp.example.com/path", "https://erp.example.com:not-a-port"):
        try:
            service.request_origin(origin=invalid, purpose="business")
        except BrowserPolicyError:
            pass
        else:
            raise AssertionError(f"Expected {invalid} to be rejected")

    request = service.request_origin(origin="https://erp.example.com", purpose="business")
    service.decide_origin_request(request_id=request["id"], approved=False)
    try:
        service.decide_origin_request(request_id=request["id"], approved=True)
    except BrowserPolicyError:
        pass
    else:
        raise AssertionError("A decided request must not be reusable")
