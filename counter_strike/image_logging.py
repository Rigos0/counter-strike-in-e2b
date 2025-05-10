from datetime import datetime
import os 

class ImageLoggingSettings:
    def __init__(self, base_path="../images"):
        """
        Initializes settings for image logging.
        Creates a unique directory for this session based on the current date and time.
        """
        self.session_timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_log_dir = os.path.join(base_path, self.session_timestamp_str)
        os.makedirs(self.session_log_dir, exist_ok=True)
        
        self._current_screenshot_path = None
        self._current_annotated_screenshot_path = None
        
        print(f"ImageLoggingSettings: Session directory created at {self.session_log_dir}")


    def generate_new_paths_for_iteration(self) -> str:
        iteration_file_timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S") 
        
        screenshot_filename = f"screenshot_{iteration_file_timestamp_str}.jpg"
        self._current_screenshot_path = os.path.join(self.session_log_dir, screenshot_filename)
        
        # Ensure annotated version uses the same unique timestamp as the screenshot
        annotated_filename = f"screenshot_annotated_{iteration_file_timestamp_str}.jpg"
        self._current_annotated_screenshot_path = os.path.join(self.session_log_dir, annotated_filename)
        
        return self._current_screenshot_path

    def get_screenshot_path(self) -> str:
        return self._current_screenshot_path

    def get_annotated_screenshot_path(self) -> str:
        return self._current_annotated_screenshot_path