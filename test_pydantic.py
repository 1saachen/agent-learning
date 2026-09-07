from pydantic import BaseModel, Field, field_validator,ValidationError

class CharacterProfile(BaseModel):
    name: str = Field(...,min_length=3,max_length=10, description="角色名称，长度在3到10个字符之间")
    age: int =Field(gt= 0,lt = 100,default=1, description="角色年龄，必须大于0且小于100")
    email_address: str = Field(..., description="角色邮箱地址，必须包含 '@' 和 '.'")
    hero_class: str = Field(..., description="角色职业，必须是 'warrior', 'mage', 'archer' 中的一个")

    @field_validator('email_address')
    @classmethod
    def validate_email(cls, value):
        if '@' not in value or '.' not in value:
            raise ValueError('Email address must contain "@" and "."')
        return value    
    
    @field_validator('hero_class')
    @classmethod
    def validate_hero_class(cls, value):
        valid_classes = ['warrior', 'mage', 'archer']
        if value not in valid_classes:
            raise ValueError(f'Hero class must be one of {valid_classes}')
        return value

data = {
    "name": "Aragorn",
    "age": 87,
    "email_address": "aragorn@example.com",
    "hero_class": "warrior"
}

print("=== 1. 测试成功案例 ===")
data_success = {
    "name": "Aragorn",
    "age": 87,
    "email_address": "aragorn@example.com",
    "hero_class": "warrior"
}
profile = CharacterProfile(**data_success)
print(profile)


print("\n=== 2. 测试失败案例 (拦截异常) ===")
data_fail = {
    "name": "Al",                     # 错误：长度不足3
    # 故意不传 age，测试 default=1 是否生效
    "email_address": "bademail.com",  # 错误：缺少 @
    "hero_class": "assassin"          # 错误：不在允许的列表中
}

try:
    bad_profile = CharacterProfile(**data_fail)
except ValidationError as e:
    # 在真实 Agent 开发中，我们会把 e.errors() 转换为字符串喂回给大模型，让它重新生成
    print(f"数据校验失败，共发现 {e.error_count()} 个错误：")
    print(e)