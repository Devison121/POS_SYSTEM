"""
Colorful terminal output utilities
"""
class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    
    @classmethod
    def success(cls, message: str) -> str:
        return f"{cls.GREEN}✓ {message}{cls.RESET}"
    
    @classmethod
    def error(cls, message: str) -> str:
        return f"{cls.RED}❌ {message}{cls.RESET}"
    
    @classmethod
    def warning(cls, message: str) -> str:
        return f"{cls.YELLOW}⚠️  {message}{cls.RESET}"
    
    @classmethod
    def info(cls, message: str) -> str:
        return f"{cls.BLUE}ℹ️  {message}{cls.RESET}"
    
    @classmethod
    def header(cls, message: str) -> str:
        return f"{cls.CYAN}=== {message} ==={cls.RESET}"