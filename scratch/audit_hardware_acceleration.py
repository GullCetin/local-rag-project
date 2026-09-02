"""
scratch/audit_hardware_acceleration.py
Foundry Local SDK ve sistemdeki DirectML / GPU / NPU execution provider ve model seçeneklerini denetler.
"""
import sys

sys.path.insert(0, r"c:\Projects\local-rag-project")

from foundry_local_sdk import Configuration, FoundryLocalManager

def main():
    print("=" * 80)
    print("HARDWARE ACCELERATION & MODEL CATALOG AUDIT")
    print("=" * 80)
    
    try:
        config = Configuration(app_name="audit-app")
        FoundryLocalManager.initialize(config)
    except Exception:
        pass
    mgr = FoundryLocalManager.instance
    try:
        models = mgr.catalog.list_models()
        print(f"Total Models in Catalog: {len(models)}")
        for m in models:
            runtime = getattr(m, "runtime", None)
            device = getattr(runtime, "device_type", None) if runtime else None
            ep = getattr(runtime, "execution_provider", None) if runtime else None
            print(f"  * Model ID: {m.id:<40} | Alias: {getattr(m, 'alias', ''):<15} | Device: {str(device):<20} | EP: {str(ep)}")
    except Exception as e:
        print(f"Error listing models: {e}")
        
    # Check onnxruntime execution providers if available
    try:
        import onnxruntime as ort
        print(f"\nAvailable ONNXRuntime Execution Providers: {ort.get_available_providers()}")
        print(f"ONNXRuntime Device: {ort.get_device()}")
    except ImportError:
        print("\nonnxruntime directly not imported in env")
    except Exception as e:
        print(f"\nError checking onnxruntime: {e}")

if __name__ == "__main__":
    main()
