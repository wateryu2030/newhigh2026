# 根 conftest：须在任何测试导入 gateway.app 之前统一 JWT 密钥，避免本机 .env 与
# create_access_token 使用的默认密钥不一致导致 401。

import os

os.environ.setdefault("JWT_SECRET_KEY", "pytest-jwt-secret-key-ci-only")
os.environ.setdefault("JWT_SECRET", "pytest-jwt-secret-key-ci-only")
