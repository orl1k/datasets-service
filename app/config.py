from pydantic import BaseSettings


class Settings(BaseSettings):
    celery_app_name: str
    rabbitmq_username: str
    rabbitmq_password: str
    rabbitmq_hostname: str
    rabbitmq_node_port_number: str
    redis_password: str
    redis_hostname: str
    flower_port: str

    class Config:
        env_file = ".env"
