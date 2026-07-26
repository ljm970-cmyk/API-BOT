import yaml
from pathlib import Path

def load_config(config_path: str = "config.yaml"):
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{config_path} 파일이 없습니다. "
            "config.yaml.example을 복사해서 설정하세요."
        )
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
