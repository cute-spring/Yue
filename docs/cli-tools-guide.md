# CLI Tools 使用指南：fzf, jq, ripgrep

## 目录

- [fzf - 模糊查找工具](#fzf---模糊查找工具)
- [jq - JSON 处理工具](#jq---json-处理工具)
- [ripgrep - 快速搜索工具](#ripgrep---快速搜索工具)
- [组合使用案例](#组合使用案例)

---

## fzf - 模糊查找工具

### 概述

fzf 是一个通用的命令行模糊查找工具，可以快速搜索文件、命令历史、进程等。

### 安装验证

```bash
fzf --version
```

### 基本用法

#### 1. 文件搜索

```bash
# 交互式搜索当前目录文件
fzf

# 搜索并打开文件
vim $(fzf)

# 搜索并进入目录
cd $(find . -type d | fzf)

# 预览文件内容
fzf --preview 'head -100 {}'
```

#### 2. 命令历史搜索

```bash
# 按 Ctrl+R 搜索历史命令（需要在 shell 中配置）
# 或在脚本中使用
history | fzf

# 搜索并执行历史命令
$(history | fzf | awk '{print $2}')
```

#### 3. 进程管理

```bash
# 搜索并杀死进程
ps aux | fzf | awk '{print $2}' | xargs kill -9

# 搜索进程并查看日志
ps aux | fzf | awk '{print $2}' | xargs tail -f /proc/{}/fd/1
```

### 高级用法

#### 1. 多文件预览

```bash
fzf --preview 'bat --color=always --style=numbers --line-range=:500 {}'
```

#### 2. 目录搜索增强

```bash
# 使用 fd 替代 find（更快）
fd --type f | fzf

# 搜索特定类型文件
fd --extension py | fzf
```

#### 3. 自定义键绑定

```bash
# 在 .zshrc 或 .bashrc 中添加
export FZF_DEFAULT_OPTS='
--color=bg+:#363a4f,bg:#24283b,spinner:#f7768e,hl:#7aa2f7
--fg:#a9b1d6,header:#7aa2f7,info:#9ece6a,pointer:#7dcfff
--marker:#7dcfff,fg+:#c0caf5,prompt:#9ece6a,hl+:#7aa2f7
'
```

### 实用案例

#### 案例 1: Git 提交历史搜索

```bash
# 搜索 git 提交记录
git log --oneline | fzf | awk '{print $1}' | xargs git show
```

#### 案例 2: Docker 容器管理

```bash
# 选择并进入容器
docker ps | fzf | awk '{print $1}' | xargs docker exec -it sh

# 查看容器日志
docker ps -a | fzf | awk '{print $1}' | xargs docker logs -f
```

#### 案例 3: Kubernetes 资源操作

```bash
# 选择 Pod 并查看日志
kubectl get pods | fzf | awk '{print $1}' | xargs kubectl logs -f

# 选择 Pod 并进入 shell
kubectl get pods | fzf | awk '{print $1}' | xargs kubectl exec -it -- /bin/sh
```

---

## jq - JSON 处理工具

### 概述

jq 是一个轻量级的命令行 JSON 处理器，可以解析、过滤、转换 JSON 数据。

### 安装验证

```bash
jq --version
```

### 基本用法

#### 1. 格式化 JSON

```bash
# 美化输出
echo '{"name":"Alice","age":30}' | jq .

# 紧凑输出
echo '{"name":"Alice","age":30}' | jq -c .

# 带颜色输出
echo '{"name":"Alice","age":30}' | jq --color-output .
```

#### 2. 访问字段

```bash
# 访问单个字段
echo '{"user":{"name":"Alice"}}' | jq '.user.name'

# 访问多个字段
echo '{"name":"Alice","age":30}' | jq '{name, age}'

# 访问数组元素
echo '[1,2,3,4]' | jq '.[0]'
echo '[1,2,3,4]' | jq '.[-1]'  # 最后一个元素
```

#### 3. 过滤数据

```bash
# 条件过滤
echo '[{"name":"Alice","age":30},{"name":"Bob","age":25}]' | jq '.[] | select(.age > 27)'

# 数组转换
echo '[1,2,3,4]' | jq 'map(. * 2)'

# 获取键名
echo '{"a":1,"b":2}' | jq 'keys'
```

### 高级用法

#### 1. 复杂查询

```bash
# 嵌套过滤
cat data.json | jq '.users[] | select(.active == true) | {name, email}'

# 分组统计
cat data.json | jq 'group_by(.category) | map({category: .[0].category, count: length})'

# 递归下降
cat data.json | jq '.. | objects | select(has("id"))'
```

#### 2. 变量和函数

```bash
# 使用变量
echo '[1,2,3]' | jq '. as $data | $data | length'

# 自定义函数
echo '[1,2,3]' | jq 'def double: . * 2; map(double)'

# 字符串操作
echo '"hello world"' | jq 'split(" ") | join("-")'
```

#### 3. 错误处理

```bash
# 安全访问（字段不存在时返回 null）
echo '{}' | jq '.user?.name'

# 提供默认值
echo '{}' | jq '.name // "Unknown"'

# 尝试多个路径
echo '{}' | jq '.user.name // .admin.name // "Guest"'
```

### 实用案例

#### 案例 1: API 响应处理

```bash
# 从 GitHub API 获取仓库信息
curl -s https://api.github.com/repos/torvalds/linux | jq '{name, description, stargazers_count}'

# 处理分页数据
curl -s "https://api.github.com/users/octocat/repos?per_page=100" | jq '.[] | {name, created_at}'
```

#### 案例 2: Kubernetes JSON 输出

```bash
# 获取所有 Pod 名称和状态
kubectl get pods -o json | jq '.items[] | {name: .metadata.name, status: .status.phase}'

# 查找运行中的 Pod
kubectl get pods -o json | jq '.items[] | select(.status.phase == "Running") | .metadata.name'
```

#### 案例 3: Docker 镜像分析

```bash
# 查看镜像详情
docker inspect nginx | jq '.[0] | {Name: .Name, Created: .Created, Size: .Size}'

# 获取所有镜像标签
docker images --format "{{.Repository}}:{{.Tag}}" | jq -R -s 'split("\n") | map(select(length > 0))'
```

#### 案例 4: 配置文件转换

```bash
# YAML 转 JSON（需要 yq）
cat config.yaml | yq -o json | jq '.database | {host, port}'

# 合并多个 JSON 文件
jq -s 'add' file1.json file2.json file3.json

# 从 JSON 生成环境变量
cat config.json | jq -r 'to_entries | map("\(.key)=\(.value)") | .[]'
```

---

## ripgrep - 快速搜索工具

### 概述

ripgrep (rg) 是一个快速的命令行搜索工具，支持正则表达式，默认忽略 .gitignore 中的文件。

### 安装验证

```bash
rg --version
```

### 基本用法

#### 1. 基础搜索

```bash
# 搜索包含关键词的文件
rg "pattern"

# 递归搜索当前目录
rg -r "pattern" .

# 忽略大小写
rg -i "pattern"

# 全词匹配
rg -w "function"
```

#### 2. 文件类型过滤

```bash
# 只搜索 Python 文件
rg -t py "pattern"

# 排除某些类型
rg -T js "pattern"

# 指定文件扩展名
rg --glob "*.md" "pattern"
```

#### 3. 上下文显示

```bash
# 显示匹配行前后各 2 行
rg -C 2 "pattern"

# 只显示匹配行前 3 行
rg -B 3 "pattern"

# 只显示匹配行后 3 行
rg -A 3 "pattern"
```

### 高级用法

#### 1. 正则表达式

```bash
# 复杂正则
rg "TODO|FIXME|XXX"

# 捕获组
rg "function\s+(\w+)" --replace '$1'

# 零宽断言
rg "(?<=def ).*(?=\()"  # 匹配函数名
```

#### 2. 输出格式化

```bash
# 只显示文件名
rg -l "pattern"

# 显示匹配计数
rg -c "pattern"

# 显示行号
rg -n "pattern"

# JSON 输出
rg --json "pattern" | jq
```

#### 3. 性能优化

```bash
# 限制搜索深度
rg --max-depth 3 "pattern"

# 限制并行度
rg --threads 4 "pattern"

# 跳过符号链接
rg --follow "pattern"
```

### 实用案例

#### 案例 1: 代码搜索

```bash
# 搜索函数定义
rg "^function\s+\w+" -t js

# 搜索 TODO 注释
rg "TODO:?.*" --context 3

# 查找未使用的导入
rg "^import.*from.*$" -t ts | sort | uniq -c | sort -rn
```

#### 案例 2: 日志分析

```bash
# 搜索错误日志
rg "ERROR|FATAL" /var/log/*.log

# 提取时间戳
rg "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}" app.log

# 统计错误类型
rg "ERROR: (\w+)" app.log | awk '{print $2}' | sort | uniq -c | sort -rn
```

#### 案例 3: 配置文件搜索

```bash
# 在 YAML 中搜索键
rg "^database:" -A 5

# 在 JSON 中搜索字段
rg '"apiKey"\s*:' --glob "*.json"

# 查找空配置
rg "^\s*#\s*$" -c
```

#### 案例 4: Git 集成

```bash
# 搜索已暂存的更改
rg "pattern" --files-with-matches | xargs git diff --cached

# 搜索特定提交的更改
git log --all --oneline | rg "fix|bug" | head -10

# 查找最近修改的文件
git log --name-only --pretty=format: | rg -v '^$' | sort | uniq -c | sort -rn | head -20
```

---

## 组合使用案例

### 案例 1: 微服务配置审计

```bash
# 查找所有包含敏感信息的配置文件
rg -l "password|secret|api_key" --glob "*.yaml" --glob "*.json" | \
  fzf --preview 'bat --color=always {}' | \
  xargs jq '.database.password // .api.secret // "not found"'
```

### 案例 2: 代码质量检查

```bash
# 查找所有 TODO 并按优先级排序
rg "TODO:?.*" -t py -t js -t ts | \
  rg -o "TODO:?\s*(HIGH|MEDIUM|LOW)?:?\s*\S+" | \
  sort | uniq -c | sort -rn
```

### 案例 3: API 调试工作流

```bash
# 获取 API 响应，提取特定字段，保存为文件
curl -s https://api.example.com/users | \
  jq '[.[] | {id, name, email}]' | \
  tee users.json | \
  jq -r '.[] | "\(.name) <\(.email)>"' | \
  fzf
```

### 案例 4: 日志分析管道

```bash
# 分析错误日志，交互式查看
rg "ERROR" app.log | \
  rg -o "ERROR: \[.*\]" | \
  sort | uniq -c | sort -rn | \
  fzf --preview 'rg "{}" app.log -A 5 -B 5'
```

### 案例 5: Docker 容器诊断

```bash
# 选择容器，检查日志，提取错误
docker ps --format "{{.Names}}" | \
  fzf | \
  xargs docker logs 2>&1 | \
  rg "error|exception|fatal" -i | \
  jq -R -s 'split("\n") | map(select(length > 0)) | .[-20:]'
```

### 案例 6: Kubernetes 故障排查

```bash
# 查找失败的 Pod，检查事件
kubectl get pods -o json | \
  jq -r '.items[] | select(.status.phase != "Running") | .metadata.name' | \
  fzf | \
  xargs kubectl describe pod | \
  rg "Warning|Error" -A 3
```

### 案例 7: Git 历史分析

```bash
# 搜索提交历史，查看具体更改
git log --all --oneline | \
  fzf --preview 'git show --stat {1}' | \
  awk '{print $1}' | \
  xargs git show | \
  rg "^\+|^\-" | \
  head -50
```

### 案例 8: 依赖审计

```bash
# 检查 package.json 中的依赖版本
cat package.json | \
  jq '.dependencies | to_entries | map("\(.key): \(.value)") | .[]' | \
  rg "^\w" | \
  fzf --preview 'npm view {1} versions --json | jq'
```

---

## 快速参考表

### fzf 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+R` | 搜索历史命令 |
| `Ctrl+T` | 搜索文件（需要配置） |
| `Alt+C` | 搜索目录（需要配置） |
| `Tab` | 选择多个 |
| `Enter` | 确认选择 |
| `Ctrl+Q` | 发送到 quickfix |

### jq 常用过滤器

| 过滤器 | 功能 |
|--------|------|
| `.foo` | 访问字段 |
| `.[]` | 遍历数组 |
| `select(.x > 5)` | 条件过滤 |
| `map(. * 2)` | 数组转换 |
| `keys` | 获取键名 |
| `group_by(.x)` | 分组 |
| `.x // "default"` | 默认值 |

### ripgrep 常用参数

| 参数 | 功能 |
|--------|------|
| `-t TYPE` | 指定文件类型 |
| `-T TYPE` | 排除文件类型 |
| `-g GLOB` | 指定 glob 模式 |
| `-C NUM` | 显示上下文行数 |
| `-l` | 只显示文件名 |
| `-c` | 显示匹配计数 |
| `-n` | 显示行号 |
| `-i` | 忽略大小写 |
| `-w` | 全词匹配 |

---

## 性能对比

### 搜索速度对比

```bash
# 在大型代码库中搜索
time rg "pattern"           # ~0.1s
time grep -r "pattern" .    # ~2.5s
time find . -name "*.py" -exec grep "pattern" {} \;  # ~15s
```

### JSON 处理对比

```bash
# 解析大型 JSON 文件
time jq '.data[] | select(.active)' large.json      # ~0.5s
time python -c "import json; ..." large.json        # ~2.0s
time node -e "const data = require(...)" large.json # ~1.5s
```

---

## 最佳实践

### 1. 管道组合

```bash
# 好的实践：单一职责，管道组合
rg "ERROR" | jq -R -s 'split("\n")' | fzf

# 避免：过于复杂的单行命令
# 如果超过 3 个管道，考虑写成脚本
```

### 2. 错误处理

```bash
# 检查命令是否成功
if rg "pattern" file.txt; then
  echo "Found matches"
else
  echo "No matches"
fi

# jq 错误处理
jq '.field // empty' file.json || echo "Invalid JSON"
```

### 3. 性能优化

```bash
# 限制搜索范围
rg "pattern" --max-depth 3

# 使用类型过滤
rg -t py -t js "pattern"

# 并行处理
rg "pattern" --threads 8
```

### 4. 可读性

```bash
# 使用变量存储中间结果
errors=$(rg "ERROR" app.log)
echo "$errors" | wc -l

# 复杂查询写成多行
jq '
  .users
  | map(select(.active))
  | group_by(.role)
  | map({role: .[0].role, count: length})
' data.json
```

---

## 故障排查

### fzf 问题

**问题**: fzf 不显示预览
```bash
# 检查是否安装了 bat 或 cat
which bat || which cat

# 测试预览命令
fzf --preview 'head -10 {}'
```

### jq 问题

**问题**: JSON 解析失败
```bash
# 验证 JSON 格式
jq empty file.json

# 检查编码
file file.json

# 使用 --slurp 处理多行 JSON
jq -s '.' multiple.json
```

### ripgrep 问题

**问题**: 搜索结果为空
```bash
# 检查是否在正确的目录
pwd

# 查看 rg 配置
rg --config

# 禁用 .gitignore
rg --no-ignore "pattern"
```

---

## 扩展阅读

- [fzf 官方文档](https://github.com/junegunn/fzf)
- [jq 官方手册](https://stedolan.github.io/jq/manual/)
- [ripgrep 使用指南](https://github.com/BurntSushi/ripgrep)
- [命令行艺术](https://github.com/learnbyexample/Command-line-text-processing)
