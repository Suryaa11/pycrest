import os
import subprocess
import sys

def manage_service_dependencies():
    base_dir = os.path.join(os.getcwd(), "services")
    
    # Ensure pipreqs is installed
    try:
        import pipreqs
    except ImportError:
        print("Installing pipreqs for dependency scanning...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pipreqs"])

    if not os.path.exists(base_dir):
        print(f"Error: {base_dir} not found.")
        return

    services = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

    for service in services:
        service_path = os.path.join(base_dir, service)
        print(f"\n--- Processing Service: {service} ---")

        # 1. Identify and Generate/Update requirements.txt
        # --force overwrites the old requirements.txt with the freshly scanned ones
        print(f"Scanning imports in {service}...")
        try:
            subprocess.run(["pipreqs", service_path, "--force"], check=True)
            print(f"Successfully updated requirements.txt for {service}")
        except subprocess.CalledProcessError as e:
            print(f"Could not scan {service}: {e}")
            continue

        # 2. Install the dependencies
        req_file = os.path.join(service_path, "requirements.txt")
        if os.path.exists(req_file):
            print(f"Installing dependencies for {service}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
                print(f"Installation complete for {service}.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install dependencies for {service}: {e}")

if __name__ == "__main__":
    manage_service_dependencies()