from typing import List


class PluginConfig:

    def __init__(self, config, context=None):
        self.config = config

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    @property
    def sessdata(self) -> str:
        return self.config.get("sessdata", "")
    
    @property
    def bili_jct(self) -> str:
        return self.config.get("bili_jct", "")
    
    @property
    def buvid3(self) -> str:
        return self.config.get("buvid3", "")
    
    @property
    def buvid4(self) -> str:
        return self.config.get("buvid4", "")
    
    @property
    def dedeuserid(self) -> str:
        return self.config.get("dedeuserid", "")

    @property
    def whitelist(self) -> List[str]:
        return self.config.get("whitelist", [])
    
    @property
    def dir_path(self) -> str:
        return self.config.get("dir_path", "")

    def update(self, key: str, value):
        self.config[key] = value
