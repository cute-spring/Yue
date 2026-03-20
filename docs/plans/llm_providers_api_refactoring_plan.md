# LLM Model Providers API Refactoring Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the `/api/models/providers` endpoint to split runtime model selection from admin model management, significantly reducing JSON payload size and frontend rendering burden.

**Architecture:** 
1. The default `GET /api/models/providers` will be optimized to only return `available_models` (allowlisted) and compute capabilities strictly for these models.
2. A new admin endpoint `GET /api/models/providers/{provider}/models` will be created to fetch the full list of supported models for a specific provider.
3. The frontend `Settings.tsx` will be refactored to lazily fetch the full model list only when a user clicks "Manage Models" for a specific provider, instead of keeping all models in memory.

**Tech Stack:** FastAPI, Python, React (SolidJS), TypeScript

---

## Chunk 1: Backend Optimization

### Task 1: Optimize the default providers endpoint

**Files:**
- Modify: `backend/app/services/llm/factory.py`

- [ ] **Step 1: Write the failing test**

```python
# In backend/tests/test_api_models_unit.py or test_model_factory_registry.py
# (Assuming a test file exists, if not, write one testing the factory list_providers)
import pytest
from app.services.llm.factory import list_providers
from unittest.mock import patch

@pytest.mark.asyncio
async def test_list_providers_runtime_mode():
    with patch('app.services.llm.factory.config_service') as mock_config:
        # Mock a provider with many models, but only 2 enabled
        mock_config.get.return_value = {
            "openai_enabled_models_mode": "allowlist",
            "openai_enabled_models": ["gpt-4o", "gpt-4-turbo"]
        }
        mock_config.get_model_capabilities.return_value = ["vision"]
        
        # We need to mock the handler.list_models to return say 10 models
        # But factory.py lists models based on the handler.
        
        # Simplified conceptual test:
        providers = await list_providers(refresh=False, admin_mode=False)
        for p in providers:
            if p["name"] == "openai":
                # In runtime mode, models should equal available_models
                assert p["models"] == p["available_models"]
                # Capability keys should only match available models
                assert set(p["model_capabilities"].keys()) == set(p["available_models"])
```

- [ ] **Step 2: Modify `list_providers` signature and logic in `factory.py`**

Modify `list_providers` to accept an `admin_mode` flag (default `False`).

```python
async def list_providers(refresh: bool = False, check_connectivity: bool = False, admin_mode: bool = False, target_provider: Optional[str] = None) -> List[Dict[str, Any]]:
    # ... existing code ...
    for name, handler in handlers.items():
        # Optimization: Skip processing other providers if target_provider is specified
        if target_provider and name.lower() != target_provider.lower():
            continue
            
        # ... existing code for getting models ...
        
        config_enabled = llm_config.get(f"{name}_enabled_models")
        enabled_mode = llm_config.get(f"{name}_enabled_models_mode")
        use_allowlist = enabled_mode == "allowlist"
        
        if isinstance(config_enabled, list) and (use_allowlist or (config_enabled and len(config_enabled) > 0)):
            available_models = [m for m in models if m in config_enabled] if models else config_enabled
        else:
            available_models = models
            
        # Optimization: Only calculate capabilities for available_models in runtime mode
        capability_models = models if admin_mode else available_models
        
        model_capabilities = {
            model_name: config_service.get_model_capabilities(name, model_name)
            for model_name in (capability_models or [])
        }
        
        explicit_model_capabilities = {}
        for model_name in (capability_models or []):
            model_info = config_service.get_model_info(f"{name}/{model_name}")
            if model_info and "capabilities" in model_info:
                explicit_model_capabilities[model_name] = model_info["capabilities"]
                
        # Optimization: Don't return the massive 'models' list in runtime mode
        returned_models = models if admin_mode else available_models
        
        # ... rest of provider_data construction ...
        provider_data = {
            "name": name,
            "configured": is_configured,
            "requirements": handler.requirements(),
            "available_models": available_models,
            "models": returned_models or [],
            "model_capabilities": model_capabilities,
            "explicit_model_capabilities": explicit_model_capabilities,
            # ...
```

- [ ] **Step 3: Run tests to verify the optimization**

Run: `cd backend && PYTHONPATH=. pytest tests/`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/llm/factory.py
git commit -m "perf: optimize list_providers payload size for runtime mode"
```

### Task 2: Create Admin Endpoint for Specific Provider

**Files:**
- Modify: `backend/app/api/models.py`

- [ ] **Step 1: Write the failing tests (Unit & Integration)**

```python
# In backend/tests/test_api_models_unit.py
def test_get_provider_admin_models_unit(client):
    # Mock list_providers and test behavior
    pass

# In backend/tests/test_api_models_integration.py (or similar integration test file)
def test_get_provider_admin_models_integration(client):
    res = client.get("/api/models/providers/openai/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "model_capabilities" in data
    # It should return a large list of models, not just the available ones
```

- [ ] **Step 2: Add new route in `models.py`**

```python
@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str, refresh: bool = Query(default=False)):
    """Admin endpoint to fetch ALL models for a specific provider with capabilities."""
    providers_list = await list_providers(refresh=refresh, admin_mode=True, target_provider=provider)
    if providers_list:
        p = providers_list[0]
        return {
            "name": p["name"],
            "models": p["models"],
            "available_models": p["available_models"],
            "model_capabilities": p["model_capabilities"],
            "explicit_model_capabilities": p["explicit_model_capabilities"]
        }
    raise HTTPException(status_code=404, detail="Provider not found")
```

- [ ] **Step 3: Run tests to verify**

Run: `cd backend && PYTHONPATH=. pytest tests/`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/models.py
git commit -m "feat: add admin endpoint to fetch full model list for specific provider"
```

---

## Chunk 2: Frontend Refactoring

### Task 3: Refactor Settings.tsx to use lazy loading for Manage Models

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Update state and `openModelManager` function**

In `Settings.tsx`, modify `openModelManager` to fetch data asynchronously and add a loading state.

```tsx
// Add loading state and cache for the modal
const [isLoadingModels, setIsLoadingModels] = createSignal(false);
const [adminModelsCache, setAdminModelsCache] = createSignal<Record<string, any>>({});
const [adminModelCapabilities, setAdminModelCapabilities] = createSignal<Record<string, string[]>>({});

// Modify openModelManager
const openModelManager = async (provider: LLMProvider) => {
  setManagingProvider(provider.name);
  setShowModelManager(true);
  
  // Check cache first
  if (adminModelsCache()[provider.name]) {
    const data = adminModelsCache()[provider.name];
    setManagedModels(data.models || []);
    setEnabledModels(new Set(data.available_models || []));
    setCapabilityOverrides(data.explicit_model_capabilities || {});
    setAdminModelCapabilities(data.model_capabilities || {});
    return;
  }

  setIsLoadingModels(true);
  try {
    // Fetch full list from new admin endpoint
    const res = await fetch(`/api/models/providers/${provider.name}/models`);
    if (!res.ok) throw new Error(`API returned ${res.status}`);
    const data = await res.json();
    
    setManagedModels(data.models || []);
    setEnabledModels(new Set(data.available_models || []));
    setCapabilityOverrides(data.explicit_model_capabilities || {});
    
    // We also need to store the full capabilities for rendering the badges in the modal
    setAdminModelCapabilities(data.model_capabilities || {});
    
    // Cache the result
    setAdminModelsCache(prev => ({ ...prev, [provider.name]: data }));
  } catch (e: any) {
    console.error("Failed to load models", e);
    showToast('error', `Failed to load models: ${e.message}`);
  } finally {
    setIsLoadingModels(false);
  }
};
```

- [ ] **Step 2: Update the modal rendering logic**

Update the modal UI to show a loading spinner while `isLoadingModels()` is true, and use `adminModelCapabilities()` instead of relying on the global `providers()` state.

```tsx
// Inside the For loop in the modal:
const inferredCaps = () => adminModelCapabilities()[model] || [];
```

Add loading state UI:
```tsx
<Show when={!isLoadingModels()} fallback={
  <div class="flex justify-center items-center py-10">
    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
  </div>
}>
  {/* Existing modal content list */}
</Show>
```

- [ ] **Step 3: Run build to verify types**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "refactor: lazy load full model lists in Settings to improve performance"
```
