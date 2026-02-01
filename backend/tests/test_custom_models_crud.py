import unittest
import requests

BASE = "http://127.0.0.1:8003"

class TestCustomModelsCrud(unittest.TestCase):
    def test_crud_flow(self):
        r = requests.get(f"{BASE}/api/models/custom")
        self.assertEqual(r.status_code, 200)
        r = requests.post(f"{BASE}/api/models/custom", json={
            "name": "my-custom",
            "base_url": "https://api.example.com/v1",
            "api_key": "****masked****",
            "model": "x-large"
        })
        self.assertEqual(r.status_code, 200)
        r = requests.get(f"{BASE}/api/models/custom")
        self.assertEqual(r.status_code, 200)
        lst = r.json()
        self.assertTrue(any(m.get("name") == "my-custom" for m in lst))
        r = requests.put(f"{BASE}/api/models/custom/my-custom", json={"api_key": "real_key_123"})
        self.assertEqual(r.status_code, 200)
        r = requests.get(f"{BASE}/api/models/custom")
        self.assertEqual(r.status_code, 200)
        lst = r.json()
        m = [x for x in lst if x.get("name") == "my-custom"][0]
        self.assertEqual(m.get("api_key"), "")
        r = requests.post(f"{BASE}/api/models/test/custom", json={
            "base_url": "https://api.example.com/v1",
            "api_key": "real_key_123",
            "model": "x-large"
        })
        self.assertEqual(r.status_code, 200)
        self.assertIn("ok", r.json())
        r = requests.delete(f"{BASE}/api/models/custom/my-custom")
        self.assertEqual(r.status_code, 200)
        r = requests.get(f"{BASE}/api/models/custom")
        self.assertEqual(r.status_code, 200)
        lst = r.json()
        self.assertFalse(any(m.get("name") == "my-custom" for m in lst))

if __name__ == "__main__":
    unittest.main()
