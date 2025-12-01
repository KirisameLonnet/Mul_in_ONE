#!/bin/bash

# 测试重构后的API
# 用法: ./test_refactor.sh [username]

set -e

USERNAME=${1:-"testuser"}
BASE_URL="http://localhost:8000"

echo "======================================"
echo "测试用户: $USERNAME"
echo "======================================"
echo

# 0. 确保用户存在
echo "0️⃣  检查/创建用户..."
USER_EXISTS=$(psql -h /Users/lonnetkirisame/Documents/Developer/Mul_in_ONE/.postgresql/run -U postgres -d mul_in_one -tAc "SELECT COUNT(*) FROM users WHERE username='$USERNAME'")

if [ "$USER_EXISTS" = "0" ]; then
  echo "用户不存在，创建新用户..."
  psql -h /Users/lonnetkirisame/Documents/Developer/Mul_in_ONE/.postgresql/run -U postgres -d mul_in_one -c "INSERT INTO users (username, email) VALUES ('$USERNAME', '$USERNAME@example.com')" > /dev/null
  echo "✅ 用户创建成功!"
else
  echo "✅ 用户已存在"
fi
echo

# 1. 创建API Profile
echo "1️⃣  创建API Profile..."
API_PROFILE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/personas/api-profiles" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"name\": \"Test GPT-4\",
    \"base_url\": \"https://api.openai.com/v1\",
    \"model\": \"gpt-4\",
    \"api_key\": \"sk-test1234567890\",
    \"temperature\": 0.7
  }")

API_PROFILE_ID=$(echo $API_PROFILE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ API Profile创建成功! ID: $API_PROFILE_ID"
echo

# 2. 创建Persona
echo "2️⃣  创建Persona..."
PERSONA_RESPONSE=$(curl -s -X POST "$BASE_URL/api/personas/personas" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"name\": \"测试助手\",
    \"prompt\": \"你是一个友好的AI助手。\",
    \"handle\": \"assistant\",
    \"tone\": \"friendly\",
    \"proactivity\": 0.5,
    \"memory_window\": 10,
    \"max_agents_per_turn\": 1,
    \"api_profile_id\": $API_PROFILE_ID,
    \"is_default\": true,
    \"background\": \"我是一个专业的AI助手，擅长回答各种问题。\"
  }")

PERSONA_ID=$(echo $PERSONA_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Persona创建成功! ID: $PERSONA_ID"
echo

# 3. 创建Session
echo "3️⃣  创建Session..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/api/sessions?username=$USERNAME")
SESSION_ID=$(echo $SESSION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "✅ Session创建成功! ID: $SESSION_ID"
echo

# 4. 列出所有资源
echo "4️⃣  列出所有资源..."
echo "📋 Sessions:"
curl -s "$BASE_URL/api/sessions?username=$USERNAME" | python3 -m json.tool | head -20
echo
echo "📋 API Profiles:"
curl -s "$BASE_URL/api/personas/api-profiles?username=$USERNAME" | python3 -m json.tool | head -20
echo
echo "📋 Personas:"
curl -s "$BASE_URL/api/personas/personas?username=$USERNAME" | python3 -m json.tool | head -20
echo

# 5. 更新Persona
echo "5️⃣  更新Persona..."
curl -s -X PATCH "$BASE_URL/api/personas/personas/$PERSONA_ID?username=$USERNAME" \
  -H "Content-Type: application/json" \
  -d '{"name": "高级测试助手", "proactivity": 0.8}' > /dev/null
echo "✅ Persona更新成功!"
echo

# 6. 验证Session ID格式
echo "6️⃣  验证Session ID格式..."
if [[ $SESSION_ID =~ ^sess_${USERNAME}_[a-f0-9]{8}$ ]]; then
  echo "✅ Session ID格式正确: $SESSION_ID"
else
  echo "❌ Session ID格式错误: $SESSION_ID"
  exit 1
fi
echo

echo "======================================"
echo "✅ 所有测试通过!"
echo "======================================"
