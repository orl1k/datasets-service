from pydantic import BaseSettings


class Settings(BaseSettings):
    celery_app_name: str = "datasets-api"
    rabbitmq_username: str
    rabbitmq_password: str
    rabbitmq_hostname: str = "rabbitmq"
    rabbitmq_node_port_number: str = "5672"
    redis_password: str
    redis_hostname: str = "redis"
    flower_port: str = "5555"

    class Config:
        env_file = ".env"
