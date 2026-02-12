import unittest
import importlib
import pkgutil
import app.api

class TestApiSmoke(unittest.TestCase):
    """
    Smoke test to ensure all API modules can be imported without syntax or runtime errors.
    This catches issues like the multiline f-string SyntaxError that broke the app.
    """
    
    def test_import_all_api_modules(self):
        """
        Dynamically find and import all modules in the app.api package.
        """
        api_package = app.api
        prefix = api_package.__name__ + "."
        
        modules_to_test = []
        for loader, module_name, is_pkg in pkgutil.walk_packages(api_package.__path__, prefix):
            modules_to_test.append(module_name)
            
        print(f"\nTesting imports for {len(modules_to_test)} API modules...")
        
        failed_imports = []
        for mod_name in modules_to_test:
            try:
                importlib.import_module(mod_name)
                print(f"  ✓ {mod_name}")
            except Exception as e:
                print(f"  ✗ {mod_name}: {e}")
                failed_imports.append((mod_name, str(e)))
                
        self.assertEqual(len(failed_imports), 0, f"Failed to import modules: {failed_imports}")

    def test_main_app_startup(self):
        """
        Ensure the main app object can be created and imported.
        """
        try:
            from app.main import app as fastapi_app
            self.assertIsNotNone(fastapi_app)
            print("  ✓ app.main:app imported successfully")
        except Exception as e:
            self.fail(f"Failed to import app.main:app: {e}")

if __name__ == "__main__":
    unittest.main()
