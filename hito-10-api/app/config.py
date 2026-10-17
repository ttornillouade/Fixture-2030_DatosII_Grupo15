"""Configuración de la API: se lee de variables de entorno o de hito-10-api/.env (no versionado)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Tiempo máximo de espera por operación contra cualquier base (segundos).
    timeout_s: float = 3.0

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "fixture2030"

    cassandra_host: str = "localhost"
    cassandra_port: int = 9042
    cassandra_keyspace: str = "fixture2030_comments"

    redis_url: str = "redis://localhost:6379/0"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_usuario: str = "neo4j"
    neo4j_password: str = ""


config = Config()
