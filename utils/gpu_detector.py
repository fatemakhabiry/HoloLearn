"""
GPU Detection and Auto-Configuration Utility
Automatically detects GPU availability and compatibility, falls back to CPU if needed.
Works on any system without manual configuration.
"""

import torch
import warnings
from typing import Dict, Any, Literal

class GPUDetector:
    """
    Automatically detects and configures GPU settings for the system.
    Handles compatibility issues and provides fallback to CPU.
    """
    
    def __init__(self):
        self.cuda_available = False
        self.gpu_compatible = False
        self.device = "cpu"
        self.gpu_name = "N/A"
        self.cuda_version = "N/A"
        self.vram_gb = 0.0
        self.compatibility_message = ""
        
        # Run detection
        self._detect_gpu()
    
    def _detect_gpu(self):
        """Detect GPU availability and compatibility"""
        
        # Check if CUDA is available
        self.cuda_available = torch.cuda.is_available()
        
        if not self.cuda_available:
            self.compatibility_message = "No CUDA-capable GPU detected. Using CPU mode."
            self.device = "cpu"
            return
        
        # Get GPU information
        try:
            self.gpu_name = torch.cuda.get_device_name(0)
            self.cuda_version = torch.version.cuda if torch.version.cuda else "Unknown"
            self.vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        except Exception as e:
            self.compatibility_message = f"Error getting GPU info: {str(e)}"
            self.device = "cpu"
            return
        
        # Check for compatibility warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                # Try to create a tensor on GPU to trigger any compatibility warnings
                test_tensor = torch.tensor([1.0]).cuda()
                del test_tensor
                torch.cuda.empty_cache()
                
                # If we get here without warnings, GPU is compatible
                if len(w) == 0:
                    self.gpu_compatible = True
                    self.device = "cuda"
                    self.compatibility_message = f"GPU compatible: {self.gpu_name}"
                else:
                    # Check if warning is about compute capability
                    for warning in w:
                        warning_msg = str(warning.message)
                        if "CUDA capability" in warning_msg or "not compatible" in warning_msg:
                            self.gpu_compatible = False
                            self.device = "cpu"
                            self.compatibility_message = (
                                f"GPU detected but not compatible: {self.gpu_name}. "
                                "PyTorch version doesn't support this GPU architecture. "
                                "Falling back to CPU mode."
                            )
                            break
                    else:
                        # Other warnings - still use GPU
                        self.gpu_compatible = True
                        self.device = "cuda"
                        self.compatibility_message = f"GPU compatible with warnings: {self.gpu_name}"
            
            except Exception as e:
                self.gpu_compatible = False
                self.device = "cpu"
                self.compatibility_message = f"GPU compatibility test failed: {str(e)}. Using CPU."
    
    def get_device(self) -> str:
        """Get the recommended device (cuda or cpu)"""
        return self.device
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get recommended configuration settings based on GPU capability
        Returns dict with OCR and processing settings
        """
        if self.device == "cuda" and self.gpu_compatible:
            # GPU-optimized settings
            config = {
                "device": "cuda",
                "easyocr_gpu": True,
                "easyocr_batch_size": self._get_optimal_batch_size(),
                "pix2tex_device": "cuda",
                "pix2tex_batch_size": 16,
                "use_gpu_for_video": True,
                "frame_extraction_batch_size": 32,
            }
        else:
            # CPU-optimized settings
            config = {
                "device": "cpu",
                "easyocr_gpu": False,
                "easyocr_batch_size": 4,
                "pix2tex_device": "cpu",
                "pix2tex_batch_size": 2,
                "use_gpu_for_video": False,
                "frame_extraction_batch_size": 4,
            }
        
        return config
    
    def _get_optimal_batch_size(self) -> int:
        """Determine optimal batch size based on VRAM"""
        if not self.gpu_compatible:
            return 4
        
        # Batch size recommendations based on VRAM
        if self.vram_gb >= 12:
            return 32
        elif self.vram_gb >= 8:
            return 24
        elif self.vram_gb >= 6:
            return 16
        elif self.vram_gb >= 4:
            return 12
        else:
            return 8
    
    def print_status(self):
        """Print GPU detection status"""
        print("=" * 80)
        print("GPU DETECTION STATUS")
        print("=" * 80)
        print(f"CUDA Available: {self.cuda_available}")
        print(f"GPU Compatible: {self.gpu_compatible}")
        print(f"Selected Device: {self.device.upper()}")
        
        if self.cuda_available:
            print(f"GPU Name: {self.gpu_name}")
            print(f"CUDA Version: {self.cuda_version}")
            print(f"VRAM: {self.vram_gb:.1f} GB")
        
        print(f"\nStatus: {self.compatibility_message}")
        print("=" * 80)
        
        # Print recommended settings
        config = self.get_config()
        print("\nRECOMMENDED SETTINGS:")
        print("-" * 80)
        for key, value in config.items():
            print(f"{key:30s}: {value}")
        print("=" * 80)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete detection summary"""
        return {
            "cuda_available": self.cuda_available,
            "gpu_compatible": self.gpu_compatible,
            "device": self.device,
            "gpu_name": self.gpu_name,
            "cuda_version": self.cuda_version,
            "vram_gb": self.vram_gb,
            "message": self.compatibility_message,
            "config": self.get_config()
        }


# Global detector instance
_gpu_detector = None

def get_gpu_detector() -> GPUDetector:
    """Get or create the global GPU detector instance"""
    global _gpu_detector
    if _gpu_detector is None:
        _gpu_detector = GPUDetector()
    return _gpu_detector


def auto_select_device() -> str:
    """
    Automatically select the best device (cuda or cpu)
    Returns: 'cuda' or 'cpu'
    """
    detector = get_gpu_detector()
    return detector.get_device()


def get_auto_config() -> Dict[str, Any]:
    """
    Get automatic configuration based on system capabilities
    Returns: Dict with recommended settings
    """
    detector = get_gpu_detector()
    return detector.get_config()


# Test function
if __name__ == "__main__":
    detector = GPUDetector()
    detector.print_status()