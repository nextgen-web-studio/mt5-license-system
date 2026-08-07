import shutil
import os

def compile_ea(mt5_id: str, expiry: str, plan: str):
    """
    Simulates the compilation of an EA by copying a template.
    """
    template_path = os.path.join(os.path.dirname(__file__), "templates", "DummyEA.exe")
    output_filename = f"InfinityTrader_{mt5_id}_{expiry}.exe"
    output_path = os.path.join(os.path.dirname(__file__), "output", output_filename)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Copy the template
    shutil.copy(template_path, output_path)
    
    return output_path
