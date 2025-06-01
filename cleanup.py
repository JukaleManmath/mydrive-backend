import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.cleanup import cleanup_storage

if __name__ == "__main__":
    print("Starting cleanup process...")
    if cleanup_storage():
        print("Cleanup completed successfully!")
    else:
        print("Cleanup failed. Check the logs for details.") 