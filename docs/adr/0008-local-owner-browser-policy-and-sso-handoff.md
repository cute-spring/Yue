# Local-owner browser policy and SSO handoff isolation

Browser collaboration uses a locally owned policy of exact HTTPS origins rather than persistent per-session trust or delegated administrator roles. Business origins permit explicit browser sessions; SSO-handoff origins permit only authentication traversal and Yue must not capture or automate them. This deliberately trades broad convenience for a revocable boundary that cannot carry browser credentials or IdP content into Yue.
