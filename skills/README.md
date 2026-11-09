# 把技能放到这里

本目录（`skills/`）用来放所有技能文件夹。**每个子文件夹就是一个技能**，例如：

```
skills/
├─ aba-keyword-miner/
│  ├─ SKILL.md          # 必须：含 YAML frontmatter (name, description)
│  ├─ run.py            # 可选：脚本
│  └─ requirements.txt  # 可选：依赖
├─ sqp-brand-analysis/
│  ├─ SKILL.md
│  └─ sqp_report.py
└─ ...（其余 20 个技能同理）
```

## SKILL.md 最小格式

```markdown
---
name: aba-keyword-miner
description: 一句话说明这个技能做什么、何时使用。
---

# 技能标题
正文说明……
```

- 文件夹名（如 `aba-keyword-miner`）会出现在 `npx` 安装时以及页面源码链接里。
- 安装脚本会原样把每个文件夹复制到 WorkBuddy 的 skills 目录，所以里面的脚本、依赖说明都一并带走。
- 注意：`skills/` 目录必须提交到仓库（不要写进 .gitignore），否则别人 `npx` 会装到空目录。
