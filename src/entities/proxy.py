from dataclasses import dataclass


@dataclass
class ProxyTelethon:
    protocol: str
    host: str
    port: int
    login: str
    password: str
